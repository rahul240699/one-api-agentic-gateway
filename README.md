# OneAPI

A gateway for AI agents to interact with multiple APIs through a single endpoint, and pay-per-use.

Agents send requests to OneAPI with a payment token. The gateway authenticates the token, deducts credits from the account's ledger, routes the request to the correct provider, and returns the result — all in one call. No individual API keys required per provider.

---

## Architecture

```
Frontend (Next.js)
    │
    ├── Chat UI  ──────────────────► SSE /api/v1/stream
    │                                      │
    │                               OpenAI agent loop
    │                                      │
    │                           tool calls → /v1/enrich
    └── Wallet sidebar ◄──────────         └─► /v1/scrape
         balance / top-up                        │
                                    PaymentMiddleware (402 gate)
                                                 │
                                          Credit Ledger
                                     (InMemoryLedger / Redis)
                                                 │
                                        Mock Providers
                                   (Apollo, ScrapeGraph, ...)
```

**MCP server** is mounted at `/mcp` — any MCP-compatible client can connect and use the same tools.

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI, Python 3.11+ |
| Agent loop | OpenAI (`gpt-4o-mini` by default) |
| MCP interface | `mcp` SDK, Streamable HTTP |
| Ledger | In-memory (async-locked) — Redis swap-in via env var |
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

Edit `.env` and set your OpenAI key:

```
OPENAI_API_KEY=sk-...
```

### 2. Backend

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn app.main:app --port 8000 --reload
```

Backend is live at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/enrich` | Profile enrichment (Apollo) — costs **10 cr** |
| `POST` | `/v1/scrape` | Web scrape (ScrapeGraph) — costs **5 cr** |
| `POST` | `/api/v1/wallet/topup` | Add credits to an account |
| `GET` | `/api/v1/wallet/activity` | Transaction history for a token |
| `GET` | `/api/v1/stream` | SSE agent run stream |
| `POST` | `/mcp/` | MCP Streamable HTTP endpoint |

All billable routes require the header: `X-Payment-Token: <your-token>`.  
Accounts are auto-created on first use with the default balance (`ONE_API_DEFAULT_BALANCE`, default `100`).

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Required. OpenAI key for the agent loop |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model used by the agent |
| `ONE_API_DEFAULT_BALANCE` | `100` | Starting credits for new accounts |
| `ONE_API_STORE` | `memory` | Ledger backend: `memory` or `redis` |
| `ONE_API_REDIS_URL` | `redis://localhost:6379/0` | Used when `ONE_API_STORE=redis` |
