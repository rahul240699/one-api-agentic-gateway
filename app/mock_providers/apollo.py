from typing import Any


async def enrich(payload: dict[str, Any]) -> dict[str, Any]:
    """Mock Apollo person/company enrichment. Returns canned data."""
    domain = payload.get("domain", "example.com")
    return {
        "domain": domain,
        "company": "Example Corp",
        "employees": 240,
        "industry": "Software",
        "contacts": [
            {"name": "Ada Lovelace", "title": "CTO", "email": f"ada@{domain}"},
        ],
    }
