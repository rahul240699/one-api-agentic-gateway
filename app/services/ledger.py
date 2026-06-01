import asyncio
import datetime
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable


class InsufficientFunds(Exception):
    """Raised when an account's balance cannot cover a debit."""

    def __init__(self, account_id: str, balance: int, amount: int):
        self.account_id = account_id
        self.balance = balance
        self.amount = amount
        super().__init__(
            f"account {account_id!r} balance {balance} < requested {amount}"
        )


@dataclass
class TxEntry:
    """A single ledger event recorded in account history."""

    kind: Literal["debit", "credit", "topup"]
    amount: int
    balance_after: int
    service: str | None  # populated for debits (provider name)
    success: bool
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat()
    )


@runtime_checkable
class LedgerStore(Protocol):
    """Backend-agnostic credit ledger. Implementations must keep debit atomic."""

    async def get_balance(self, account_id: str) -> int: ...

    async def debit(self, account_id: str, amount: int, service: str | None = None) -> int:
        """Atomically subtract `amount`; return remaining balance.

        Raises InsufficientFunds if the balance cannot cover `amount`.
        """
        ...

    async def credit(self, account_id: str, amount: int) -> int:
        """Add `amount` to the account; return the new balance."""
        ...

    async def topup(self, account_id: str, amount: int) -> int:
        """Operator-initiated top-up; logs a 'topup' entry and returns new balance."""
        ...

    async def get_history(self, account_id: str) -> list[TxEntry]:
        """Return the full transaction history for an account."""
        ...


class InMemoryLedger:
    """Async-locked, in-process ledger. Accounts are auto-seeded on first touch."""

    def __init__(self, default_balance: int):
        self._default_balance = default_balance
        self._balances: dict[str, int] = {}
        self._history: dict[str, list[TxEntry]] = {}
        self._lock = asyncio.Lock()
        # Optional async callback(account_id, new_balance) fired after debit/topup
        self._on_balance_change = None

    def set_balance_callback(self, callback) -> None:
        self._on_balance_change = callback

    def seed_balance(self, account_id: str, balance: int) -> None:
        """Pre-seed an account balance (called at startup from user store)."""
        self._balances[account_id] = balance

    def _seed(self, account_id: str) -> int:
        """Seed account if new; return current balance (must be called under lock)."""
        return self._balances.setdefault(account_id, self._default_balance)

    def _append(self, account_id: str, entry: TxEntry) -> None:
        self._history.setdefault(account_id, []).append(entry)

    async def get_balance(self, account_id: str) -> int:
        async with self._lock:
            return self._seed(account_id)

    async def debit(self, account_id: str, amount: int, service: str | None = None) -> int:
        async with self._lock:
            balance = self._seed(account_id)
            if balance < amount:
                self._append(account_id, TxEntry(
                    kind="debit", amount=amount, balance_after=balance,
                    service=service, success=False,
                ))
                raise InsufficientFunds(account_id, balance, amount)
            balance -= amount
            self._balances[account_id] = balance
            self._append(account_id, TxEntry(
                kind="debit", amount=amount, balance_after=balance,
                service=service, success=True,
            ))
        if self._on_balance_change:
            await self._on_balance_change(account_id, balance)
        return balance

    async def credit(self, account_id: str, amount: int) -> int:
        async with self._lock:
            balance = self._seed(account_id)
            balance += amount
            self._balances[account_id] = balance
            self._append(account_id, TxEntry(
                kind="credit", amount=amount, balance_after=balance,
                service=None, success=True,
            ))
            return balance

    async def topup(self, account_id: str, amount: int) -> int:
        async with self._lock:
            balance = self._seed(account_id)
            balance += amount
            self._balances[account_id] = balance
            self._append(account_id, TxEntry(
                kind="topup", amount=amount, balance_after=balance,
                service=None, success=True,
            ))
        if self._on_balance_change:
            await self._on_balance_change(account_id, balance)
        return balance

    async def get_history(self, account_id: str) -> list[TxEntry]:
        async with self._lock:
            self._seed(account_id)
            return list(self._history.get(account_id, []))


class RedisLedger:
    """Redis-backed ledger (swap target). Keeps check-and-decrement atomic via Lua.

    Stub: wire a real redis.asyncio client in `dependencies.get_ledger` when
    ONE_API_STORE=redis. Left unimplemented in the first cut.
    """

    def __init__(self, redis_url: str, default_balance: int):  # pragma: no cover
        raise NotImplementedError(
            "RedisLedger is scaffolded but not implemented; use ONE_API_STORE=memory."
        )
