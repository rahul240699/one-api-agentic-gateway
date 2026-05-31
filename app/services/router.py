from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.mock_providers import apollo, scrapegraph

Provider = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    cost: int
    handler: Provider


class UnknownEndpoint(Exception):
    """Raised when a path has no registered provider."""


class ProviderRouter:
    """Maps generic gateway endpoints to mock provider callables + their cost."""

    def __init__(self, costs: dict[str, int]):
        self._registry: dict[str, ProviderSpec] = {
            "/v1/enrich": ProviderSpec("apollo", costs["/v1/enrich"], apollo.enrich),
            "/v1/scrape": ProviderSpec(
                "scrapegraph", costs["/v1/scrape"], scrapegraph.scrape
            ),
        }

    def cost_for(self, path: str) -> int | None:
        """Cost in credits for a billable path, or None if the path isn't billable."""
        spec = self._registry.get(path)
        return spec.cost if spec else None

    def service_name_for(self, path: str) -> str | None:
        """Provider name for a billable path, or None."""
        spec = self._registry.get(path)
        return spec.name if spec else None

    async def dispatch(self, path: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        """Run the provider for `path`; return (provider_name, data)."""
        spec = self._registry.get(path)
        if spec is None:
            raise UnknownEndpoint(path)
        data = await spec.handler(payload)
        return spec.name, data
