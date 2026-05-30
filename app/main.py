from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.dependencies import get_router
from app.middleware.payment import PaymentMiddleware
from app.models.envelope import BillingBlock, ResponseEnvelope
from app.services.router import ProviderRouter, UnknownEndpoint


def create_app() -> FastAPI:
    app = FastAPI(title="one-api", description="Agentic API gateway with 402 billing")
    app.add_middleware(PaymentMiddleware)

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
