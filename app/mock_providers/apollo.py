from typing import Any

import httpx

from app.config import provider_keys
from app.mock_providers.jina import ProviderUnavailable

BASE_URL = "https://api.hunter.io/v2"


def _check(resp: httpx.Response, provider: str = "Hunter") -> None:
    if resp.status_code == 401:
        raise ProviderUnavailable(f"{provider} API key is invalid or expired.")
    if resp.status_code == 429:
        raise ProviderUnavailable(f"{provider} rate limit reached — server is out of credits for this API.")
    if resp.status_code >= 400:
        raise ProviderUnavailable(f"{provider} returned {resp.status_code}: {resp.text[:200]}")


async def enrich(payload: dict[str, Any]) -> dict[str, Any]:
    """Enrich a contact or domain using Hunter.io.

    Modes (selected automatically by the payload):
      - email only          → email-verifier (deliverability + confidence)
      - domain + name       → email-finder (find email for a specific person)
      - domain only         → domain-search (list contacts at a company)
    """
    api_key = provider_keys.hunter_api_key
    if not api_key:
        raise ProviderUnavailable("Hunter API key is not configured on the server.")

    email = payload.get("email", "")
    domain = payload.get("domain", "")
    first_name = payload.get("first_name", "")
    last_name = payload.get("last_name", "")

    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:

            if email and not domain:
                resp = await client.get(
                    "/email-verifier",
                    params={"email": email, "api_key": api_key},
                )
                _check(resp)
                data = resp.json().get("data", {})
                return {
                    "mode": "email_verifier",
                    "email": data.get("email"),
                    "deliverability": data.get("deliverability"),
                    "confidence": data.get("score"),
                    "first_name": data.get("first_name"),
                    "last_name": data.get("last_name"),
                    "company": data.get("company"),
                    "domain": data.get("domain"),
                }

            if domain and (first_name or last_name):
                params: dict[str, str] = {"domain": domain, "api_key": api_key}
                if first_name:
                    params["first_name"] = first_name
                if last_name:
                    params["last_name"] = last_name
                resp = await client.get("/email-finder", params=params)
                _check(resp)
                data = resp.json().get("data", {})
                return {
                    "mode": "email_finder",
                    "email": data.get("email"),
                    "confidence": data.get("score"),
                    "first_name": data.get("first_name"),
                    "last_name": data.get("last_name"),
                    "company": data.get("company"),
                    "domain": domain,
                }

            if domain:
                resp = await client.get(
                    "/domain-search",
                    params={"domain": domain, "api_key": api_key, "limit": 10},
                )
                _check(resp)
                data = resp.json().get("data", {})
                contacts = [
                    {
                        "email": e.get("value"),
                        "first_name": e.get("first_name"),
                        "last_name": e.get("last_name"),
                        "confidence": e.get("confidence"),
                        "type": e.get("type"),
                    }
                    for e in data.get("emails", [])
                ]
                return {
                    "mode": "domain_search",
                    "domain": domain,
                    "company": data.get("organization"),
                    "contacts": contacts,
                    "total": data.get("meta", {}).get("total"),
                }

    except httpx.RequestError as exc:
        raise ProviderUnavailable(f"Hunter network error: {exc}") from exc

    raise ValueError("Provide 'email', 'domain', or 'domain' + 'first_name'/'last_name'")
