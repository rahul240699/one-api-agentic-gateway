from typing import Any, Literal

from pydantic import BaseModel, Field, PositiveInt


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


# --- Wallet management models ---

class TopupRequest(BaseModel):
    """Input for POST /api/v1/wallet/topup."""

    token: str = Field(..., min_length=1, description="Account token to top up")
    amount: PositiveInt = Field(..., description="Credits to add (must be > 0)")


class TopupResponse(BaseModel):
    """Returned after a successful top-up."""

    token: str
    amount_added: int
    new_balance: int
    currency: str = "credits"


class TxEntryOut(BaseModel):
    """One entry in the wallet activity log (read model for the API)."""

    kind: Literal["debit", "credit", "topup"]
    amount: int
    balance_after: int
    service: str | None
    success: bool
    timestamp: str


class ActivityResponse(BaseModel):
    """Returned by GET /api/v1/wallet/activity."""

    token: str
    balance: int
    history: list[TxEntryOut]
