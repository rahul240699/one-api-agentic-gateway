import os
from typing import Any

import httpx

from app.mock_providers.jina import ProviderUnavailable  # shared exception

BASE_URL = "https://google.serper.dev"


async def search(payload: dict[str, Any]) -> dict[str, Any]:
    """Run a Google search via Serper and return organic results."""
    api_key = os.getenv("SERPER_API_KEY", "")
    if not api_key:
        raise ProviderUnavailable("Serper API key is not configured on the server.")

    query = payload.get("q") or payload.get("query", "")
    if not query:
        raise ValueError("'q' (query) is required")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                BASE_URL + "/search",
                json={
                    "q": query,
                    "gl": payload.get("gl", "us"),
                    "hl": payload.get("hl", "en"),
                    "num": payload.get("num", 5),
                },
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
            )
    except httpx.RequestError as exc:
        raise ProviderUnavailable(f"Serper network error: {exc}") from exc

    if resp.status_code in (401, 403):
        raise ProviderUnavailable("Serper API key is invalid or expired.")
    if resp.status_code == 429:
        raise ProviderUnavailable("Serper rate limit reached — server is out of credits for this API.")
    if resp.status_code >= 400:
        raise ProviderUnavailable(f"Serper returned {resp.status_code}: {resp.text[:200]}")

    body = resp.json()
    organic = [
        {
            "position": r.get("position"),
            "title": r.get("title"),
            "url": r.get("link"),
            "snippet": r.get("snippet"),
        }
        for r in body.get("organic", [])
    ]
    return {
        "query": query,
        "organic": organic,
        "answer_box": body.get("answerBox"),
        "knowledge_graph": body.get("knowledgeGraph"),
        "credits_used": body.get("credits"),
    }
