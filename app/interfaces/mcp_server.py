"""MCP interface for the gateway.

Exposes three tools over Streamable HTTP. Each tool makes a real HTTP request
back into the FastAPI gateway (loopback), so the existing 402 payment handshake
and ledger-deduction middleware are triggered naturally — the MCP server is just
another paying agent presenting an X-Payment-Token.
"""

import logging
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("agentic-commerce-gateway")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

# Where the gateway is reachable, and the payment token this agent presents.
GATEWAY_URL = os.getenv("ONE_API_GATEWAY_URL", "http://localhost:8000")
PAYMENT_TOKEN = os.getenv("ONE_API_MCP_TOKEN", "mcp-agent")

# stateless_http + json_response keep responses as single JSON bodies, which
# play nicely behind the gateway's BaseHTTPMiddleware (no SSE buffering issues).
mcp = FastMCP(
    "Agentic-Commerce-Gateway",
    streamable_http_path="/",
    stateless_http=True,
    json_response=True,
)


async def _call_gateway(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Issue the billable request to the gateway and surface the billing result."""
    logger.info("→ [MCP→Gateway] POST %s token=%s payload=%s", path, PAYMENT_TOKEN, payload)
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as client:
        resp = await client.post(
            path, json=payload, headers={"X-Payment-Token": PAYMENT_TOKEN}
        )
    body = resp.json()
    logger.info("← [Gateway→MCP] %s %s", resp.status_code, body)

    if resp.status_code == 402:
        # Pass the payment challenge back to the caller instead of raising.
        return {"status": "payment_required", "challenge": body}
    resp.raise_for_status()
    return body


@mcp.tool()
async def enrich_profile(email: str) -> dict[str, Any]:
    """Enrich a person/company profile from an email address (Apollo provider)."""
    logger.info("[JSON-RPC] tools/call enrich_profile(email=%r)", email)
    domain = email.split("@")[-1] if "@" in email else email
    return await _call_gateway("/v1/enrich", {"email": email, "domain": domain})


@mcp.tool()
async def scrape_page(url: str) -> dict[str, Any]:
    """Scrape a web page and return its extracted content (ScrapeGraph provider)."""
    logger.info("[JSON-RPC] tools/call scrape_page(url=%r)", url)
    return await _call_gateway("/v1/scrape", {"url": url})


@mcp.tool()
async def execute_action(action_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Execute a billable transaction; dispatched to /v1/{action_type} via the gateway."""
    logger.info("[JSON-RPC] tools/call execute_action(action_type=%r, payload=%s)", action_type, payload)
    return await _call_gateway(f"/v1/{action_type}", payload)


@mcp.tool()
async def get_wallet_status() -> dict[str, Any]:
    """Return the current balance and transaction history for this agent's account.

    Read-only — this tool cannot add credits. Contact an operator to top up.
    """
    logger.info("[JSON-RPC] tools/call get_wallet_status(token=%r)", PAYMENT_TOKEN)
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=10.0) as client:
        resp = await client.get(
            "/api/v1/wallet/activity",
            headers={"X-Payment-Token": PAYMENT_TOKEN},
        )
    body = resp.json()
    logger.info("← [Gateway→MCP] wallet_status %s balance=%s", resp.status_code, body.get("balance"))
    resp.raise_for_status()
    return body
