# Research Shop

An autonomous research shop: customers pay with crypto (any chain, via NEAR Intents / 1Click), the agent detects the payment, generates an AI research report, and splits the revenue automatically.

## How it works

```
Customer requests a report
        │
        ▼
Agent gets a 1Click quote ──► unique deposit address + exact amount
        │
Customer sends USDC (from Ethereum, Base, Solana, Near, ...)
        │
        ▼
Agent polls 1Click status until SETTLED
        │
        ▼
Claude generates the research report
        │
        ▼
Revenue split (owner 70% / contributors 20% / reserve 10%)
Everything logged to public_ledger.json
        │
        ▼
Report delivered (file, JSON response, or web page)
```

## Repository layout

| Path | Purpose |
|---|---|
| `main.py` | FastAPI web app: order API, payment-status polling, report delivery, serves the customer page |
| `index.html` | Customer-facing demo page (enter topic → pay → report appears) |
| `agentd.py` | CLI daemon for fully automatic order fulfillment (request → pay → detect → deliver) |
| `payment_demo.py` | Minimal payment-receiving demo (quote → deposit address → wait) |
| `demo.py` | Minimal end-to-end order demo (constraints → report → split) |
| `src/payment.py` | 1Click integration: quotes, deposit addresses, status polling |
| `src/agent.py` | Order orchestration: constraints, inference, revenue split, ledger |
| `src/inference.py` | Claude (Anthropic-compatible) report generation |
| `src/constraints.py` | Business rules: kill switch, minimum price, daily spend limit |
| `src/config.py` | YAML config loader |
| `src/ledger.py` | Public ledger (JSON) logging |
| `config.yaml` | All settings: prices, limits, revenue split, payment recipient, model |
| `tests/` | Test suite (`pytest`) |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key   # Claude-compatible API key
```

Configure `config.yaml`:

- `recipient` / `refund_to` — your NEAR account ID (where settled payments land)
- `min_price_usd`, `max_daily_inference_spend_usd` — guardrails
- `revenue_split` — owner / contributors / reserve shares
- `model` — any model your API endpoint supports (default: `claude-haiku-5-5`)

## Usage

### Web app (customer-facing)

```bash
uvicorn main:app --reload
# open http://localhost:8000
```

Customer flow: enter a topic → the page shows a deposit address + exact amount → pay → the page polls and the report appears when payment settles.

API endpoints:

- `POST /api/order` `{"topic": "...", "amount_usd": 8.0}` → order ID + deposit address + amount
- `GET /api/order/{id}` → current status; generates the report automatically once payment settles

### CLI daemon (fully automatic)

```bash
python agentd.py request "Current adoption of NEAR Intents" 8.0   # get payment details
python agentd.py                                                   # daemon: poll payments, auto-deliver reports to reports/
python agentd.py status                                            # inspect orders
```

### Demos

```bash
python demo.py              # one order end-to-end
python payment_demo.py      # quote + deposit address only (--no-wait skips waiting)
```

## Deploy to Vercel

1. Push the repo to GitHub.
2. On vercel.com: **Add New → Project** → import the repo (Python runtime is auto-detected; `main.py` exports the `app`).
3. Add environment variable `ANTHROPIC_API_KEY` (Settings → Environment Variables).
4. Deploy. The site serves the customer page and the order API.

### Deployment notes

- **Order state is ephemeral** on serverless (stored in `/tmp`, per-instance). Fine for a demo; use a database (e.g., Vercel KV/Postgres) for production.
- Report generation runs inside the status-polling request after settlement, so no separate worker is needed on Vercel.
- The `agentd.py` daemon is for local/self-hosted use; Vercel serverless cannot run long-lived polling loops.

## How the payment detection works

1. `src/payment.py` requests a quote from `1click.chaindefuser.com` (`POST /v0/quote`) with `depositType: INTENTS` — the response contains a unique deposit address and exact input amount.
2. The customer sends the exact amount to that address from any supported chain (the quote handles cross-chain routing).
3. `GET /v0/status?depositAddress=...` is polled until the status is `SETTLED`, `EXPIRED`, or `REFUNDED`.
4. On `SETTLED`, the order proceeds to report generation. Refunds/expirations are recorded and reported as `payment_failed`.

## Revenue split

On each successful order the payment is split per `config.yaml` (default):

- **owner** 70% — you
- **contributors** 20%
- **reserve** 10%

Every order (amount, inference cost, splits, report preview, model used, timestamp) is appended to `public_ledger.json`.

## Safety & guardrails

- `kill_switch: true` in `config.yaml` pauses all order acceptance instantly.
- Minimum price and daily inference spend limits are enforced by `src/constraints.py`.
- The API key is read from the environment only — never commit keys.

## Tests

```bash
pytest tests/
```
