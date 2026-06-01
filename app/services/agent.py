"""Real AI agent loop.

Runs an OpenAI chat-completion with tool-calling against the MCP tool
definitions, then dispatches each tool call directly to the gateway so the
402 payment handshake and ledger deduction fire on every invocation.

Yields SSE-ready event dicts that the stream endpoint converts to text.
"""

import json
import logging
from typing import Any, AsyncGenerator

import httpx
from openai import AsyncOpenAI

from app.config import openai_settings

logger = logging.getLogger("agentic-commerce-gateway")

# Provider display names shown on the RoutingCard in the UI.
PROVIDER_LABELS: dict[str, str] = {
    "enrich_profile": "Mock Apollo V2 Engine",
    "scrape_page": "ScrapeGraph Extractor",
    "jina_scrape": "Jina Reader",
    "firecrawl_scrape": "Firecrawl",
    "get_weather": "Weatherbit",
    "web_search": "Serper (Google Search)",
    "execute_action": "Gateway Dispatcher",
    "get_wallet_status": "Ledger Read",
}

# OpenAI function-call schemas for each MCP tool.
TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "enrich_profile",
            "description": "Enrich a person or company profile by email address using the Apollo provider.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Email address to enrich"},
                },
                "required": ["email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_page",
            "description": "Scrape a web page and return its extracted text and links.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL to scrape"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jina_scrape",
            "description": "Scrape any public web page and return clean markdown content using Jina Reader. Best for articles, docs, and blogs. Costs 2 credits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL of the page to scrape"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "firecrawl_scrape",
            "description": "Scrape a web page using Firecrawl for high-quality markdown extraction including JS-rendered content. Costs 5 credits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL of the page to scrape"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather conditions for a city or coordinates. Costs 1 credit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name (e.g. 'London' or 'New York,US')"},
                    "lat": {"type": "number", "description": "Latitude (use with lon instead of city)"},
                    "lon": {"type": "number", "description": "Longitude (use with lat instead of city)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search Google via Serper and return organic results, answer boxes, and knowledge panels. Costs 10 credits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Search query"},
                    "num": {"type": "integer", "description": "Number of results (default 5, max 10)"},
                },
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_wallet_status",
            "description": "Check the agent's current credit balance and transaction history. Call this when asked about budget or credits.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

SYSTEM_PROMPT = """\
You are an agentic assistant with access to real APIs backed by a pay-per-use billing ledger. \
Each tool call deducts credits from the wallet.

Available tools and their costs:
- enrich_profile   — Apollo profile enrichment by email         (10 cr)
- jina_scrape      — Jina Reader: clean markdown from any URL   (2 cr)
- firecrawl_scrape — Firecrawl: JS-rendered page scraping       (5 cr)
- get_weather      — Weatherbit: current weather by city/coords (1 cr)
- web_search       — Serper: Google search results              (10 cr)
- get_wallet_status — Check remaining balance (free)

Guidelines:
- Choose the cheapest tool that answers the question. Use jina_scrape (2 cr) over firecrawl_scrape (5 cr) unless the page is JS-heavy.
- For questions about current events or facts, prefer web_search.
- For page content extraction, prefer jina_scrape.
- Always interpret and summarise tool results — never return raw JSON to the user.
- Mention credit cost naturally when relevant ("That scrape cost 2 credits, you have X remaining.").
- Never make up data. Only use what the tools return.
"""


# Maps LLM tool names → (gateway path, payload builder).
# get_wallet_status is handled inline (no gateway charge).
_TOOL_DISPATCH: dict[str, tuple[str | None, Any]] = {
    "enrich_profile":   ("/v1/enrich",    lambda a: {"email": a.get("email", ""), "domain": a.get("email", "").split("@")[-1]}),
    "scrape_page":      ("/v1/scrape",    lambda a: {"url": a.get("url", "")}),
    "jina_scrape":      ("/v1/jina",      lambda a: {"url": a.get("url", "")}),
    "firecrawl_scrape": ("/v1/firecrawl", lambda a: {"url": a.get("url", "")}),
    "get_weather":      ("/v1/weather",   lambda a: a),
    "web_search":       ("/v1/search",    lambda a: {"q": a.get("q", ""), "num": a.get("num", 5)}),
    "get_wallet_status": (None, None),
}


async def _call_gateway_direct(
    tool_name: str,
    arguments: dict[str, Any],
    gateway_url: str,
    payment_token: str,
) -> dict[str, Any]:
    """Call the gateway directly with the user's payment token.

    This ensures the 402 middleware charges the correct account, not the
    MCP server's internal account.
    """
    if tool_name == "get_wallet_status":
        async with httpx.AsyncClient(base_url=gateway_url, timeout=10.0) as client:
            resp = await client.get(
                "/api/v1/wallet/activity",
                headers={"X-Payment-Token": payment_token},
            )
        resp.raise_for_status()
        return resp.json()

    path_entry = _TOOL_DISPATCH.get(tool_name)
    if not path_entry or path_entry[0] is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    path, build_payload = path_entry
    async with httpx.AsyncClient(base_url=gateway_url, timeout=15.0) as client:
        resp = await client.post(
            path,
            json=build_payload(arguments),
            headers={"X-Payment-Token": payment_token},
        )
    resp.raise_for_status()
    return resp.json()


async def run_agent(
    message: str,
    payment_token: str,
    gateway_url: str = "http://localhost:8000",
) -> AsyncGenerator[tuple[str, dict[str, Any]], None]:
    """Run the full agent loop; yield (event_name, event_data) pairs.

    The caller wraps these in SSE frames.
    """
    if not openai_settings.openai_api_key:
        yield "error", {"message": "OPENAI_API_KEY is not configured."}
        return

    client = AsyncOpenAI(api_key=openai_settings.openai_api_key)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]

    yield "thinking", {"message": f'Thinking about: "{message}"'}

    # Agentic loop — keep going until the model stops requesting tool calls.
    while True:
        response = await client.chat.completions.create(
            model=openai_settings.openai_model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        choice = response.choices[0]
        msg = choice.message

        # Append assistant turn to history.
        messages.append(msg.model_dump(exclude_unset=True))

        # No tool calls → final answer.
        if not msg.tool_calls:
            yield "answer", {"message": msg.content or ""}
            break

        # Process each tool call the model requested.
        for tc in msg.tool_calls:
            tool_name = tc.function.name
            try:
                arguments = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            provider = PROVIDER_LABELS.get(tool_name, tool_name)
            logger.info("[AGENT] tool_call %s(%s)", tool_name, arguments)

            yield "tool_start", {
                "tool": tool_name,
                "provider": provider,
                "arguments": arguments,
            }

            try:
                result = await _call_gateway_direct(
                    tool_name, arguments, gateway_url, payment_token
                )

                # Extract billing info if the gateway returned it.
                billing = result.get("billing", {})
                cost = billing.get("amount_deducted")
                remaining = billing.get("remaining_credits")

                logger.info("[AGENT] tool_result %s → billing=%s", tool_name, billing)

                yield "tool_result", {
                    "tool": tool_name,
                    "provider": provider,
                    "cost": cost,
                    "remaining_credits": remaining,
                    "data": result,
                }

                # Feed the result back into the conversation.
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

            except Exception as exc:
                logger.error("[AGENT] tool_error %s: %s", tool_name, exc)
                yield "tool_error", {"tool": tool_name, "error": str(exc)}
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps({"error": str(exc)}),
                })
