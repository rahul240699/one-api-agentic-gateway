import asyncio

import pytest

from app.services.ledger import InMemoryLedger, InsufficientFunds


def test_debit_returns_remaining():
    async def scenario():
        ledger = InMemoryLedger(default_balance=100)
        assert await ledger.debit("acct", 30) == 70
        assert await ledger.get_balance("acct") == 70

    asyncio.run(scenario())


def test_insufficient_funds_raises_and_preserves_balance():
    async def scenario():
        ledger = InMemoryLedger(default_balance=5)
        with pytest.raises(InsufficientFunds):
            await ledger.debit("acct", 10)
        assert await ledger.get_balance("acct") == 5

    asyncio.run(scenario())


def test_concurrent_debits_do_not_oversell():
    async def scenario():
        ledger = InMemoryLedger(default_balance=100)
        results = await asyncio.gather(
            *(ledger.debit("acct", 1) for _ in range(100)),
            return_exceptions=True,
        )
        assert [r for r in results if isinstance(r, Exception)] == []
        assert await ledger.get_balance("acct") == 0

    asyncio.run(scenario())


def test_credit_refunds():
    async def scenario():
        ledger = InMemoryLedger(default_balance=10)
        await ledger.debit("acct", 10)
        assert await ledger.credit("acct", 10) == 10

    asyncio.run(scenario())
