from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.dependencies import get_router
from app.interfaces.mcp_server import mcp
from app.middleware.payment import PaymentMiddleware
from app.models.envelope import BillingBlock, ResponseEnvelope
from app.services.router import ProviderRouter, UnknownEndpoint


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
    app.add_middleware(PaymentMiddleware)
    # MCP tools loop back over HTTP to /v1/* so the 402 + ledger middleware fires.
    app.mount("/mcp", mcp_app)

    @app.exception_handler(UnknownEndpoint)
    async def _unknown_endpoint(request: Request, exc: UnknownEndpoint) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": f"No provider for {exc}"})

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

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

    return app


app = create_app()
