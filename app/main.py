import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.dependencies import get_ledger, get_router
from app.interfaces.mcp_server import mcp
from app.middleware.payment import PaymentMiddleware, PAYMENT_HEADER
from app.models.envelope import (
    ActivityResponse,
    BillingBlock,
    ResponseEnvelope,
    TopupRequest,
    TopupResponse,
    TxEntryOut,
)
from app.services.agent import run_agent
from app.services.ledger import LedgerStore
from app.services.router import ProviderRouter, UnknownEndpoint

logger = logging.getLogger("agentic-commerce-gateway")


def create_app() -> FastAPI:
    # Build the MCP ASGI app first so its session manager exists for the lifespan.
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with mcp.session_manager.run():
            yield

    app = FastAPI(
        title="one-api",
        description="Agentic API gateway with 402 billing",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(PaymentMiddleware)
    # MCP tools loop back over HTTP to /v1/* so the 402 + ledger middleware fires.
    app.mount("/mcp", mcp_app)

    @app.exception_handler(UnknownEndpoint)
    async def _unknown_endpoint(request: Request, exc: UnknownEndpoint) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": f"No provider for {exc}"})

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/wallet/topup", response_model=TopupResponse)
    async def wallet_topup(
        body: TopupRequest,
        ledger: LedgerStore = Depends(get_ledger),
    ) -> TopupResponse:
        new_balance = await ledger.topup(body.token, body.amount)
        logger.info(
            "💰 [TOPUP] token=%s +%d credits → balance=%d",
            body.token, body.amount, new_balance,
        )
        return TopupResponse(
            token=body.token,
            amount_added=body.amount,
            new_balance=new_balance,
        )

    @app.get("/api/v1/wallet/activity", response_model=ActivityResponse)
    async def wallet_activity(
        x_payment_token: str = Header(..., description="Account token"),
        ledger: LedgerStore = Depends(get_ledger),
    ) -> ActivityResponse:
        balance = await ledger.get_balance(x_payment_token)
        history = await ledger.get_history(x_payment_token)
        return ActivityResponse(
            token=x_payment_token,
            balance=balance,
            history=[TxEntryOut(**vars(e)) for e in history],
        )

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

    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    @app.get("/api/v1/stream")
    async def agent_stream(
        message: str = "",
        token: str = "",
        ledger: LedgerStore = Depends(get_ledger),
    ) -> StreamingResponse:

        async def generate() -> AsyncGenerator[str, None]:
            if not token:
                yield _sse("error", {"message": "Provide ?token= to stream."})
                return

            async for event_name, event_data in run_agent(
                message=message,
                payment_token=token,
                gateway_url="http://localhost:8000",
            ):
                yield _sse(event_name, event_data)

            # After agent finishes, emit the final balance and close.
            balance = await ledger.get_balance(token)
            yield _sse("done", {"balance": balance})

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app()
