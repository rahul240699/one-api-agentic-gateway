from typing import Any

import httpx

from app.config import provider_keys
from app.mock_providers.jina import ProviderUnavailable

BASE_URL = "https://api.hunter.io/v2"


def _check(resp: httpx.Response) -> None:
    if resp.status_code == 401:
        raise ProviderUnavailable("Hunter API key is invalid or expired.")
    if resp.status_code == 429:
        raise ProviderUnavailable("Hunter rate limit reached — server is out of credits for this API.")
    if resp.status_code >= 400:
        raise ProviderUnavailable(f"Hunter returned {resp.status_code}: {resp.text[:200]}")


def _str(payload: dict, key: str) -> str:
    """Return a stripped string value, treating None/missing as empty string."""
    return str(payload.get(key) or "").strip()


async def enrich(payload: dict[str, Any]) -> dict[str, Any]:
    """Enrich a contact or domain using Hunter.io.

    Mode is selected automatically:
      - email only                      → /email-verifier
      - domain + first_name/last_name   → /email-finder
      - domain only                     → /domain-search
    """
    api_key = provider_keys.hunter_api_key
    if not api_key:
        raise ProviderUnavailable("Hunter API key is not configured on the server.")

    email      = _str(payload, "email")
    domain     = _str(payload, "domain")
    first_name = _str(payload, "first_name")
    last_name  = _str(payload, "last_name")

    # Derive domain from email if only email was given
    if email and not domain:
        domain = email.split("@")[-1] if "@" in email else ""

    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:

            # Mode 1: verify a specific email address
            if email and not (first_name or last_name):
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

            # Mode 2: find email for a named person at a domain
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

            # Mode 3: search all known contacts at a domain
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

    raise ProviderUnavailable(
        "Could not determine Hunter mode. Provide 'email', 'domain', or 'domain' + 'first_name'/'last_name'."
    )
