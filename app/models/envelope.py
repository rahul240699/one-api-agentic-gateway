from typing import Any

from pydantic import BaseModel


class BillingBlock(BaseModel):
    """Billing summary attached to every successful response."""

    amount_deducted: int
    remaining_credits: int
    currency: str = "credits"


class ResponseEnvelope(BaseModel):
    """Uniform success envelope wrapping a provider's payload."""

    provider: str
    data: dict[str, Any]
    billing: BillingBlock


class PaymentRequired(BaseModel):
    """Body returned with an HTTP 402 challenge."""

    endpoint: str
    cost: int
    currency: str = "credits"
    balance: int | None = None
    message: str
