from typing import Any

import httpx

from app.config import provider_keys
from app.mock_providers.jina import ProviderUnavailable

BASE_URL = "https://api.firecrawl.dev/v1"


async def scrape(payload: dict[str, Any]) -> dict[str, Any]:
    """Scrape a URL via Firecrawl and return markdown + metadata."""
    api_key = provider_keys.firecrawl_api_key
    if not api_key:
        raise ProviderUnavailable("Firecrawl API key is not configured on the server.")

    url = payload.get("url", "")
    if not url:
        raise ValueError("url is required")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                BASE_URL + "/scrape",
                json={"url": url, "formats": ["markdown"]},
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
    except httpx.RequestError as exc:
        raise ProviderUnavailable(f"Firecrawl network error: {exc}") from exc

    if resp.status_code in (401, 403):
        raise ProviderUnavailable("Firecrawl API key is invalid or expired.")
    if resp.status_code == 429:
        raise ProviderUnavailable("Firecrawl rate limit reached — server is out of credits for this API.")
    if resp.status_code >= 400:
        raise ProviderUnavailable(f"Firecrawl returned {resp.status_code}: {resp.text[:200]}")

    body = resp.json()
    data = body.get("data", {})
    metadata = data.get("metadata", {})
    return {
        "url": url,
        "title": metadata.get("title", ""),
        "description": metadata.get("description", ""),
        "markdown": data.get("markdown", ""),
        "status_code": metadata.get("statusCode"),
    }
