from pydantic import BaseModel


class Account(BaseModel):
    """A pre-funded account identified by its payment token."""

    account_id: str
    balance: int
