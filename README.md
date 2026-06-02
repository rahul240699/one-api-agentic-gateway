# OneAPI

A gateway for AI agents to interact with multiple APIs through a single endpoint, pay-per-use.

Agents register once, receive a `sk-...` API key, and use it to call any provider — web search, page scraping, weather, contact enrichment — through a single authenticated endpoint. Credits are deducted per call. No individual provider keys needed by the caller.

---

## Architecture

```
Frontend (Next.js)          External Agent / Script
    │                                │
    │  login → get sk-... key        │  POST /api/v1/agent
    │                                │  X-OneAPI-Key: sk-...
    ├── Chat UI ──► SSE /api/v1/stream
    │                    │
    └── Wallet sidebar   │
         balance / keys  │
                         ▼
                  OpenAI agent loop
                         │
             tool calls (X-OneAPI-Key)
                         │
                ┌────────┴────────┐
          /v1/jina        /v1/search
          /v1/firecrawl   /v1/weather
          /v1/enrich      /v1/scrape
                         │
            PaymentMiddleware (401 / 402 gate)
                         │
                   Credit Ledger
              (InMemoryLedger / Redis)
                         │
               Real Provider APIs
          (Jina · Firecrawl · Weatherbit
           Serper · Hunter.io · ScrapeGraph)
```

**MCP server** is also mounted at `/mcp` — any MCP-compatible client can connect and call the same tools.

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, Python 3.11+ |
| Agent loop | OpenAI (`gpt-4o-mini` by default) |
| MCP interface | `mcp` SDK, Streamable HTTP |
| Ledger | In-memory (async-locked) — Redis swap via env var |
| Auth | bcrypt passwords · `sk-` API keys · JSON file store |
| Frontend | Next.js 16, TypeScript, Tailwind CSS |
| Streaming | SSE (`EventSource`) |

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd one-api
cp .env.example .env
```

Edit `.env` — at minimum set your OpenAI key and the provider keys you want active:

```env
OPENAI_API_KEY=sk-...

# Real provider keys (leave blank to disable that tool)
JINA_API_KEY=jina_...
FIRECRAWL_API_KEY=fc-...
WEATHERBIT_API_KEY=...
SERPER_API_KEY=...
HUNTER_API_KEY=...
```

### 2. Backend

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --port 8000 --reload
```

Backend → `http://localhost:8000`  
Interactive docs → `http://localhost:8000/docs`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`, register an account, and start chatting with the agent.

---

## Getting Your API Key

### Option A — Frontend (recommended for humans)

1. Open `http://localhost:3000`
2. Click **Register**, enter your email and password
3. You land on the dashboard. Your `sk-...` key is shown in the **API Keys** section of the sidebar
4. Click the copy icon next to any key to copy the full value
5. Click **Generate** to create additional keys — all keys share the same account balance

### Option B — REST (for scripts and CI)

```bash
# Register
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpassword"}'
```

```json
{
  "email": "you@example.com",
  "api_key": "sk-e6133abe1ffb...",
  "balance": 100
}
```

```bash
# Login (returns the same key)
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpassword"}'

# Generate a second key for the same account
curl -s -X POST http://localhost:8000/api/v1/auth/keys \
  -H "X-OneAPI-Key: sk-e6133abe1ffb..."

# List all keys on the account
curl -s http://localhost:8000/api/v1/auth/keys \
  -H "X-OneAPI-Key: sk-e6133abe1ffb..."
```

---

## Using the Agent (Agent Skills)

### Synchronous — JSON in / JSON out (best for scripts and agents)

```bash
curl -s -X POST http://localhost:8000/api/v1/agent \
  -H "X-OneAPI-Key: sk-..." \
  -H "Content-Type: application/json" \
  -d '{"message": "Scrape https://www.imdb.com/title/tt0068646/ and summarise it"}'
```

Response:

```json
{
  "answer": "The Godfather (1972) — Rating 9.2/10 ...",
  "tool_calls": [
    {
      "event": "tool_result",
      "tool": "jina_scrape",
      "provider": "Jina Reader",
      "cost": 2,
      "remaining_credits": 98,
      "data": { ... }
    }
  ],
  "balance": 98
}
```

### Streaming — SSE (best for chat UIs)

```bash
curl -N "http://localhost:8000/api/v1/stream?message=What+is+the+weather+in+Tokyo&token=sk-..."
```

Events fired in order: `thinking` → `tool_start` → `tool_result` → `answer` → `done`

---

## Available Tools and Costs

| Tool | Provider | Cost | Best for |
| --- | --- | --- | --- |
| `web_search` | Serper (Google) | **10 cr** | Current facts, news, general questions |
| `enrich_profile` | Hunter.io | **10 cr** | Email lookup, domain contact search |
| `firecrawl_scrape` | Firecrawl | **5 cr** | JS-rendered pages, SPAs |
| `jina_scrape` | Jina Reader | **2 cr** | Static pages, articles, docs |
| `get_weather` | Weatherbit | **1 cr** | Current weather by city or coordinates |
| `get_wallet_status` | Ledger | **free** | Check balance and transaction history |

The agent automatically picks the cheapest tool that answers the question. You can also be explicit in your message — see [skills/agent-skills.md](skills/agent-skills.md) for prompt examples.

### Example prompts

```
# Web scraping
"Scrape https://news.ycombinator.com and give me the top 5 stories"
"What does the pricing page at https://vercel.com/pricing say?"

# Search
"What are the latest AI models released in 2025?"
"Search for the best Python async libraries"

# Weather
"What's the weather in London right now?"
"Is it a good day to visit Paris this weekend?"

# Contact enrichment
"Find the email for Elon Musk at tesla.com"
"Who works at stripe.com? Give me a list of contacts"
"Is john@example.com a valid email address?"

# Wallet
"How many credits do I have left?"
"Show my transaction history"
```

---

## Wallet Management

```bash
# Check balance and history
curl -s http://localhost:8000/api/v1/wallet/activity \
  -H "X-OneAPI-Key: sk-..."

# Top up credits (self-service)
curl -s -X POST http://localhost:8000/api/v1/wallet/topup \
  -H "X-OneAPI-Key: sk-..." \
  -H "Content-Type: application/json" \
  -d '{"amount": 100}'
```

---

## All API Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/register` | — | Create account, returns `api_key` |
| `POST` | `/api/v1/auth/login` | — | Login, returns `api_key` |
| `GET` | `/api/v1/auth/me` | Key | Current user info + all keys |
| `GET` | `/api/v1/auth/keys` | Key | List all API keys on the account |
| `POST` | `/api/v1/auth/keys` | Key | Generate a new API key |
| `POST` | `/api/v1/agent` | Key | Synchronous agent — JSON in / JSON out |
| `GET` | `/api/v1/stream` | `?token=` | SSE agent stream |
| `GET` | `/api/v1/wallet/activity` | Key | Balance + transaction history |
| `POST` | `/api/v1/wallet/topup` | Key | Add credits to your account |
| `POST` | `/v1/enrich` | Key | Direct Hunter.io call — 10 cr |
| `POST` | `/v1/jina` | Key | Direct Jina scrape — 2 cr |
| `POST` | `/v1/firecrawl` | Key | Direct Firecrawl scrape — 5 cr |
| `POST` | `/v1/weather` | Key | Direct Weatherbit call — 1 cr |
| `POST` | `/v1/search` | Key | Direct Serper search — 10 cr |
| `POST` | `/mcp/` | — | MCP Streamable HTTP endpoint |

**Auth:** all `Key` routes require the header `X-OneAPI-Key: sk-...`

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Required. Powers the agent loop |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model for the agent |
| `JINA_API_KEY` | — | Jina Reader — page scraping (2 cr) |
| `FIRECRAWL_API_KEY` | — | Firecrawl — JS-rendered scraping (5 cr) |
| `WEATHERBIT_API_KEY` | — | Weatherbit — current weather (1 cr) |
| `SERPER_API_KEY` | — | Serper — Google search (10 cr) |
| `HUNTER_API_KEY` | — | Hunter.io — contact enrichment (10 cr) |
| `ONE_API_DEFAULT_BALANCE` | `100` | Credits granted on registration |
| `ONE_API_STORE` | `memory` | Ledger backend: `memory` or `redis` |
| `ONE_API_REDIS_URL` | `redis://localhost:6379/0` | Redis URL (when store=redis) |
| `ONE_API_KEY` | — | API key used by the MCP server itself |
