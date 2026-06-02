import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import get_cors_origins, get_gateway_url, settings
from app.dependencies import get_ledger, get_router, get_user_store
from app.interfaces.mcp_server import mcp
from app.middleware.payment import PAYMENT_HEADER, PaymentMiddleware
from app.mock_providers.jina import ProviderUnavailable
from app.models.envelope import (
    ActivityResponse,
    BillingBlock,
    ResponseEnvelope,
    TopupRequest,
    TopupResponse,
    TxEntryOut,
)
from app.routers.auth import router as auth_router
from app.services.agent import run_agent
from app.services.ledger import InMemoryLedger, LedgerStore
from app.services.router import ProviderRouter, UnknownEndpoint
from app.services.user_store import UserStore

logger = logging.getLogger("agentic-commerce-gateway")


def create_app() -> FastAPI:
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Seed in-memory ledger from persisted user balances.
        store = get_user_store()
        ledger = get_ledger()
        if isinstance(ledger, InMemoryLedger):
            for user in store.all_users():
                for key in user.api_keys:
                    ledger.seed_balance(key, user.balance)
            ledger.set_balance_callback(store.update_balance)

        async with mcp.session_manager.run():
            yield

    app = FastAPI(
        title="one-api",
        description="Agentic API gateway with 402 billing",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    app.add_middleware(PaymentMiddleware)
    app.mount("/mcp", mcp_app)
    app.include_router(auth_router)

    # ------------------------------------------------------------------ exception handlers

    @app.exception_handler(UnknownEndpoint)
    async def _unknown_endpoint(request: Request, exc: UnknownEndpoint) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": f"No provider for {exc}"})

    @app.exception_handler(ProviderUnavailable)
    async def _provider_unavailable(request: Request, exc: ProviderUnavailable) -> JSONResponse:
        logger.warning("[PROVIDER] unavailable: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"detail": str(exc), "error": "provider_unavailable"},
        )

    @app.exception_handler(ValueError)
    async def _bad_payload(request: Request, exc: ValueError) -> JSONResponse:
        logger.warning("[GATEWAY] bad payload: %s", exc)
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "error": "bad_request"},
        )

    # ------------------------------------------------------------------ health

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # ------------------------------------------------------------------ wallet

    @app.post("/api/v1/wallet/topup", response_model=TopupResponse)
    async def wallet_topup(
        body: TopupRequest,
        x_oneapi_key: str = Header(..., alias=PAYMENT_HEADER),
        store: UserStore = Depends(get_user_store),
        ledger: LedgerStore = Depends(get_ledger),
    ) -> TopupResponse:
        user = await store.get_by_api_key(x_oneapi_key)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API key.")
        new_balance = await ledger.topup(x_oneapi_key, body.amount)
        logger.info("💰 [TOPUP] %s +%d → balance=%d", user.email, body.amount, new_balance)
        return TopupResponse(
            token=x_oneapi_key,
            amount_added=body.amount,
            new_balance=new_balance,
        )

    @app.get("/api/v1/wallet/activity", response_model=ActivityResponse)
    async def wallet_activity(
        x_oneapi_key: str = Header(..., alias=PAYMENT_HEADER),
        store: UserStore = Depends(get_user_store),
        ledger: LedgerStore = Depends(get_ledger),
    ) -> ActivityResponse:
        user = await store.get_by_api_key(x_oneapi_key)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API key.")
        balance = await ledger.get_balance(x_oneapi_key)
        history = await ledger.get_history(x_oneapi_key)
        return ActivityResponse(
            token=x_oneapi_key,
            balance=balance,
            history=[TxEntryOut(**vars(e)) for e in history],
        )

    # ------------------------------------------------------------------ gateway (billable)

    @app.post("/v1/{capability}", response_model=ResponseEnvelope)
    async def gateway(
        capability: str,
        request: Request,
        payload: dict[str, Any] | None = None,
        router: ProviderRouter = Depends(get_router),
    ) -> ResponseEnvelope:
        provider, data = await router.dispatch(request.url.path, payload or {})
        return ResponseEnvelope(
            provider=provider,
            data=data,
            billing=BillingBlock(
                amount_deducted=request.state.amount_deducted,
                remaining_credits=request.state.remaining_credits,
            ),
        )

    # ------------------------------------------------------------------ SSE stream

    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    @app.get("/api/v1/stream")
    async def agent_stream(
        message: str = "",
        token: str = "",
        ledger: LedgerStore = Depends(get_ledger),
        store: UserStore = Depends(get_user_store),
    ) -> StreamingResponse:

        async def generate() -> AsyncGenerator[str, None]:
            if not token:
                yield _sse("error", {"message": "Provide ?token= to stream."})
                return
            user = await store.get_by_api_key(token)
            if not user:
                yield _sse("error", {"message": "Invalid API key."})
                return

            async for event_name, event_data in run_agent(
                message=message,
                payment_token=token,
                gateway_url=get_gateway_url(),
            ):
                yield _sse(event_name, event_data)

            balance = await ledger.get_balance(token)
            yield _sse("done", {"balance": balance})

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ------------------------------------------------------------------ synchronous agent endpoint

    @app.post("/api/v1/agent")
    async def agent_sync(
        request: Request,
        x_oneapi_key: str = Header(..., alias=PAYMENT_HEADER),
        store: UserStore = Depends(get_user_store),
        ledger: LedgerStore = Depends(get_ledger),
    ) -> dict[str, Any]:
        """Synchronous agent endpoint for external callers.

        POST {"message": "..."} with X-OneAPI-Key header.
        Returns full answer + tool call trace + final balance.
        """
        user = await store.get_by_api_key(x_oneapi_key)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API key.")

        body = await request.json()
        message = body.get("message", "")
        if not message:
            raise HTTPException(status_code=400, detail="'message' is required.")

        answer = ""
        tool_calls: list[dict] = []

        async for event_name, event_data in run_agent(
            message=message,
            payment_token=x_oneapi_key,
            gateway_url="http://localhost:8000",
        ):
            if event_name == "answer":
                answer = event_data.get("message", "")
            elif event_name in ("tool_result", "tool_error"):
                tool_calls.append({"event": event_name, **event_data})
            elif event_name == "error":
                raise HTTPException(status_code=500, detail=event_data.get("message"))

        balance = await ledger.get_balance(x_oneapi_key)
        return {"answer": answer, "tool_calls": tool_calls, "balance": balance}

    return app


app = create_app()
