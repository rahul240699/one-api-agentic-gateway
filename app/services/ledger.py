import asyncio
from typing import Protocol, runtime_checkable


class InsufficientFunds(Exception):
    """Raised when an account's balance cannot cover a debit."""

    def __init__(self, account_id: str, balance: int, amount: int):
        self.account_id = account_id
        self.balance = balance
        self.amount = amount
        super().__init__(
            f"account {account_id!r} balance {balance} < requested {amount}"
        )


@runtime_checkable
class LedgerStore(Protocol):
    """Backend-agnostic credit ledger. Implementations must keep debit atomic."""

    async def get_balance(self, account_id: str) -> int: ...

    async def debit(self, account_id: str, amount: int) -> int:
        """Atomically subtract `amount`; return remaining balance.

        Raises InsufficientFunds if the balance cannot cover `amount`.
        """
        ...

    async def credit(self, account_id: str, amount: int) -> int:
        """Add `amount` to the account; return the new balance."""
        ...


class InMemoryLedger:
    """Async-locked, in-process ledger. Accounts are auto-seeded on first touch."""

    def __init__(self, default_balance: int):
        self._default_balance = default_balance
        self._balances: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def get_balance(self, account_id: str) -> int:
        async with self._lock:
            return self._balances.setdefault(account_id, self._default_balance)

    async def debit(self, account_id: str, amount: int) -> int:
        async with self._lock:
            balance = self._balances.setdefault(account_id, self._default_balance)
            if balance < amount:
                raise InsufficientFunds(account_id, balance, amount)
            balance -= amount
            self._balances[account_id] = balance
            return balance

    async def credit(self, account_id: str, amount: int) -> int:
        async with self._lock:
            balance = self._balances.setdefault(account_id, self._default_balance)
            balance += amount
            self._balances[account_id] = balance
            return balance


class RedisLedger:
    """Redis-backed ledger (swap target). Keeps check-and-decrement atomic via Lua.

    Stub: wire a real redis.asyncio client in `dependencies.get_ledger` when
    ONE_API_STORE=redis. Left unimplemented in the first cut.
    """

    def __init__(self, redis_url: str, default_balance: int):  # pragma: no cover
        raise NotImplementedError(
            "RedisLedger is scaffolded but not implemented; use ONE_API_STORE=memory."
        )
