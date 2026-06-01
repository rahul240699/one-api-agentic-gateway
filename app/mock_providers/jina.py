import os
from typing import Any

import httpx


class ProviderUnavailable(Exception):
    """Raised when the upstream provider refuses the request (quota, auth, etc.)."""


BASE_URL = "https://r.jina.ai"


async def scrape(payload: dict[str, Any]) -> dict[str, Any]:
    """Scrape a URL via Jina Reader and return structured markdown content."""
    api_key = os.getenv("JINA_API_KEY", "")
    if not api_key:
        raise ProviderUnavailable("Jina API key is not configured on the server.")

    url = payload.get("url", "")
    if not url:
        raise ValueError("url is required")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                BASE_URL + "/",
                json={"url": url},
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
    except httpx.RequestError as exc:
        raise ProviderUnavailable(f"Jina network error: {exc}") from exc

    if resp.status_code in (401, 403):
        raise ProviderUnavailable("Jina API key is invalid or expired.")
    if resp.status_code == 429:
        raise ProviderUnavailable("Jina rate limit reached — server is out of credits for this API.")
    if resp.status_code >= 400:
        raise ProviderUnavailable(f"Jina returned {resp.status_code}: {resp.text[:200]}")

    body = resp.json()
    data = body.get("data", {})
    return {
        "url": url,
        "title": data.get("title", ""),
        "content": data.get("content", ""),
        "usage": data.get("usage", {}),
    }
