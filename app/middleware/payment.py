from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.dependencies import get_ledger, get_router
from app.models.envelope import PaymentRequired
from app.services.ledger import InsufficientFunds

PAYMENT_HEADER = "X-Payment-Token"


def _challenge(endpoint: str, cost: int, message: str, balance: int | None = None) -> JSONResponse:
    body = PaymentRequired(endpoint=endpoint, cost=cost, balance=balance, message=message)
    return JSONResponse(
        status_code=402,
        content=body.model_dump(),
        headers={"X-Payment-Required": "true", "X-Price": str(cost)},
    )


class PaymentMiddleware(BaseHTTPMiddleware):
    """Gate billable routes behind the 402 handshake + credit ledger."""

    async def dispatch(self, request: Request, call_next):
        router = get_router()
        path = request.url.path
        cost = router.cost_for(path)

        # Not a billable route -> pass straight through.
        if cost is None:
            return await call_next(request)

        token = request.headers.get(PAYMENT_HEADER)
        if not token:
            return _challenge(path, cost, f"Provide {PAYMENT_HEADER} to access {path}.")

        ledger = get_ledger()
        service = router.service_name_for(path)
        try:
            remaining = await ledger.debit(token, cost, service=service)
        except InsufficientFunds as exc:
            return _challenge(
                path, cost, "Insufficient credits.", balance=exc.balance
            )

        # Hand billing context to the route handler.
        request.state.account_id = token
        request.state.amount_deducted = cost
        request.state.remaining_credits = remaining

        try:
            response = await call_next(request)
        except Exception:
            # Downstream failed after we charged -> refund so failures don't burn credits.
            await ledger.credit(token, cost)
            raise

        if response.status_code >= 400:
            await ledger.credit(token, cost)

        return response
