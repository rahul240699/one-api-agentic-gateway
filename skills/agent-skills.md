# Agent Skills — OneAPI Tool Reference

Example prompts agents can send to the gateway, and what to expect back.
Each call deducts credits from the agent's wallet automatically.

---

## web_search — Serper (Google Search)
**Cost:** 10 credits per call

Use when you need current facts, news, or answers to general questions.

**Example prompts:**
```
Search for the latest news on OpenAI's GPT-5 release.
Who won the 2024 US presidential election?
What is the current price of Bitcoin?
Find the top 5 Python web frameworks in 2025.
```

**What the tool returns:**
- `organic` — list of results with `title`, `url`, `snippet`, `position`
- `answer_box` — direct answer if Google surfaces one (e.g. a definition or fact)
- `knowledge_graph` — entity info for well-known subjects

---

## jina_scrape — Jina Reader
**Cost:** 2 credits per call

Use when you need the full content of a specific web page in clean markdown.
Best for articles, documentation pages, and blogs.

**Example prompts:**
```
Summarise the content at https://example.com/blog/ai-agents
Extract the key points from https://docs.python.org/3/library/asyncio.html
What does this page say? https://openai.com/research/gpt-4
```

**What the tool returns:**
- `title` — page title
- `content` — full page text as markdown
- `url` — the scraped URL

---

## firecrawl_scrape — Firecrawl
**Cost:** 5 credits per call

Use when a page is JavaScript-rendered and Jina returns incomplete content.
Higher quality extraction for SPAs and dynamic pages.

**Example prompts:**
```
Scrape the pricing page at https://vercel.com/pricing
Get the content from this React app: https://app.example.com/dashboard
Extract the changelog from https://github.com/org/repo/releases
```

**What the tool returns:**
- `title` — page title
- `description` — meta description
- `markdown` — full extracted content
- `status_code` — HTTP status of the scraped page

---

## get_weather — Weatherbit
**Cost:** 1 credit per call

Use to fetch current weather conditions for any city or coordinates.

**Example prompts:**
```
What's the weather in London right now?
Is it raining in Tokyo?
What's the temperature in New York, US?
Get weather for lat 48.8566, lon 2.3522
```

**What the tool returns:**
- `city`, `country` — location
- `temp_c` — temperature in Celsius
- `feels_like_c` — apparent temperature
- `humidity_pct` — relative humidity
- `wind_spd_ms` — wind speed in m/s
- `description` — e.g. "Overcast clouds"
- `uv` — UV index
- `aqi` — air quality index

---

## enrich_profile — Apollo (mock)
**Cost:** 10 credits per call

Enrich a contact's profile from their email address. Returns company and contact info.

**Example prompts:**
```
Enrich the profile for ada@example.com
What company does john@acme.io work for?
Get company info for the owner of support@startup.io
```

**What the tool returns:**
- `domain`, `company`, `industry`, `employees`
- `contacts` — list of people with `name`, `title`, `email`

---

## get_wallet_status — Ledger (free)
**Cost:** 0 credits

Check the agent's current balance and full transaction history.

**Example prompts:**
```
How many credits do I have left?
Show me my transaction history.
What's my current wallet balance?
How much did the last search cost?
```

**What the tool returns:**
- `balance` — current credit balance
- `history` — list of transactions with `kind`, `amount`, `service`, `timestamp`

---

## Credit Strategy Tips

| Goal | Best tool | Cost |
|------|-----------|------|
| Answer a factual question | `web_search` | 10 cr |
| Get full page content (static) | `jina_scrape` | 2 cr |
| Get full page content (JS app) | `firecrawl_scrape` | 5 cr |
| Current weather | `get_weather` | 1 cr |
| Profile lookup by email | `enrich_profile` | 10 cr |
| Check budget | `get_wallet_status` | 0 cr |

**Rule of thumb:** always check `get_wallet_status` before running a multi-step workflow to make sure you have enough credits.
