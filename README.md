# Research Shop

**A one-person AI research firm.** A single autonomous agent that sells short market/tech/crypto reports, accepts payment in any token via NEAR Intents, buys its own inference, pays its contributors **onchain**, and obeys hard human-set constraints. Humans set the rules in a config file — the agent runs the company.

## The 2 minute demo

1. Open the deployed site (Vercel URL in the repo settings) — or run `uvicorn main:app` locally.
2. Type a topic, click **Buy report — $8.00**. You get a unique deposit address + exact amount.
3. Send 8 USDC from any supported chain (Ethereum, Base, Solana, NEAR…). Cross-chain routing is handled by 1Click; the quote expires in 10 minutes (unused deposits auto-refund).
4. The page detects the payment, Claude generates the report, and it renders in place.
5. In the background: revenue splits **70% owner / 20% contributors / 10% compute reserve**, the contributors share is paid **on-chain** to the contributors account by the agent's own restricted key, and the full order is appended to the public ledger.

No CLI needed for the demo loop — but `agentd.py` and `demo.py` (below) show the same flow headless.

## Why this 

- **"Company of one"**: the agent does everything a firm does — sell, produce, pay suppliers (inference), pay staff (contributors), keep books (ledger) — while humans only set guardrails in `config.yaml`.
- **Real economic loop, not a mock**: payments settle through live 1Click solvers; payouts are real NEAR `ft_transfer` transactions; every step is auditable in `public_ledger.json`.
- **Security by custody design**: the agent never holds the owner's full-access key. It signs with its own **function-call access key**, allowlisted in config to exactly one contract and one method — revocable from any NEAR wallet.
- **Human control**: kill switch, minimum price, daily inference spend cap — enforced in code before any money moves.

## Architecture

```
                       config.yaml  (human-set constraints: kill switch,
                              │      min price, daily spend cap, splits,
                              │      agent-key allowlist)
                              ▼
Customer ── topic ──►  [ Agent ]  ──► 1Click quote ──► unique deposit address
                              ▲                                     │
                              │                              customer pays
                              │                              (any chain)
                    polls /v0/status                                 │
                              │                                     ▼
                       payment SETTLED ◄────────────── solvers fill intent
                              │
              ┌───────────────┼──────────────────┐
              ▼               ▼                  ▼
        Claude report   on-chain payout     public ledger
        (inference,     contributors 20%    (amount, cost, splits,
         cost logged)   via restricted      tx hash, model, timestamp)
                        function-call key
              └───────────────┴──────────────────┘
                              ▼
                    report delivered to customer
```

**Custody model (security track):** payments never touch the agent — 1Click routes settled funds directly to the owner's NEAR account (`recipient`). The agent's signing key is a *function-call access key* on the owner account, restricted by config (`agent_key.allowed_contracts` / `allowed_methods`) to USDC `ft_transfer` only; anything else is rejected before signing. The owner's full-access key is never present in the agent's environment.

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
| `src/near_tx.py` | NEAR transaction borsh serialization + Ed25519 signing for the agent's restricted key |
| `src/payout.py` | On-chain contributor payouts with allowlist enforcement (custody model) |
| `config.yaml` | All settings: prices, limits, revenue split, payment recipient, model |
| `tests/` | Test suite (`pytest`) |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # then fill in your real keys
. .env                           # or set variables directly in your shell
```

Environment variables (see `.env.example`):

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | for real reports | Claude-compatible inference key |
| `AGENT_NEAR_PRIVATE_KEY` | for live payouts | agent's restricted function-call key (hex) |
| `OUTLAYER_API_KEY` | optional | reserved for OutLayer custody integration |
| `ZAI_API_KEY` | optional | unused since the Anthropic switch; kept for compatibility |

Never commit real keys: `.env` is gitignored, and on Vercel keys go in **Settings → Environment Variables** instead. Demo mode needs no keys at all.

Configure `config.yaml`:

- `recipient` / `refund_to` — your NEAR account ID (where settled payments land)
- `min_price_usd`, `max_daily_inference_spend_usd` — guardrails
- `revenue_split` — owner / contributors / reserve shares
- `split.contributors_account` — where the 20% contributors share is paid on-chain
- `agent_key` — the agent's restricted key: which contracts/methods it may call (its spend authority)
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

### Creating the agent's restricted key (for live payouts)

1. In a NEAR wallet (Meteor, MyNearWallet, etc.), add a **function-call access key** on the owner account, restricted to the USDC contract and the `ft_transfer` method.
2. Export its private key hex as `AGENT_NEAR_PRIVATE_KEY`.
3. Mirror the same allowlist in `config.yaml` → `agent_key` (defense in depth: both the blockchain-level grant and the agent's own pre-signing check must agree).

Without this key the full flow still works — payouts are recorded as `payout_pending` in the ledger instead of being sent.

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

Every order (amount, inference cost, splits, report preview, model used, timestamp) is appended to `public_ledger.json`. When the agent key is configured, the contributors share is additionally settled on-chain via `ft_transfer` with the order id in the memo — the tx hash lands in the ledger too.

## Safety & guardrails

- `kill_switch: true` in `config.yaml` pauses all order acceptance instantly.
- Minimum price and daily inference spend limits are enforced by `src/constraints.py`.
- The agent's signing capability is allowlisted twice: at the NEAR protocol level (function-call key grant) and again in `src/payout.py` before any transaction is signed.
- The API key is read from the environment only — never commit keys.
- Ledger writes fall back to `/tmp` on read-only filesystems (Vercel), so orders never fail on logging.

## Tests

```bash
pytest tests/
```
