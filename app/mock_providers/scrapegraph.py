from typing import Any


async def scrape(payload: dict[str, Any]) -> dict[str, Any]:
    """Mock ScrapeGraph page scrape. Returns canned data."""
    url = payload.get("url", "https://example.com")
    return {
        "url": url,
        "title": "Example Domain",
        "text": "This domain is for use in illustrative examples.",
        "links": ["https://www.iana.org/domains/example"],
    }
