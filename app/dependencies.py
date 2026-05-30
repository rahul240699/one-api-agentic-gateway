from functools import lru_cache

from app.config import settings
from app.services.ledger import InMemoryLedger, LedgerStore, RedisLedger
from app.services.router import ProviderRouter


@lru_cache
def get_ledger() -> LedgerStore:
    """The single seam for swapping ledger backends."""
    if settings.store == "redis":
        return RedisLedger(settings.redis_url, settings.default_balance)
    return InMemoryLedger(settings.default_balance)


@lru_cache
def get_router() -> ProviderRouter:
    return ProviderRouter(settings.costs)
