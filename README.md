# Research Shop

**A one-person AI research firm.** A single autonomous agent that sells short market/tech/crypto reports, accepts payment in any token via NEAR Intents, buys its own inference, pays its contributors **on-chain**, and obeys hard human-set constraints. Humans set the rules in a config file — the agent runs the company.

## Try it in two minutes

1. Open the deployed site, or run `uvicorn main:app` locally.
2. Type a topic, then click **Try demo (simulated, no payment)** to see the full cycle with zero risk.
3. For the real flow, click **Buy report** and send 1 USDC to the deposit address shown (a QR code is displayed for wallet apps).
4. The page detects the payment, Claude writes the report, and the report renders in place.
5. In the background: revenue splits **70% owner / 20% contributors / 10% compute reserve**, the contributors share is paid **on-chain** by the agent's own restricted key, and the full order is appended to the public ledger.

Quotes expire in 10 minutes and unclaimed deposits refund automatically.

## Why this wins

- **"Company of one"**: the agent does everything a firm does — sell, produce, pay suppliers (inference), pay staff (contributors), keep books (ledger) — while humans only set guardrails in `config.yaml`.
- **Real economic loop, not a mock**: payments settle through live 1Click solvers; payouts are real NEAR `ft_transfer` transactions; every step is auditable in `public_ledger.json`.
- **Security by custody design**: the agent never holds the owner's full-access key. It signs with its own **function-call access key**, allowlisted in config to exactly one contract and one method — revocable from any NEAR wallet.
- **Human control**: kill switch, minimum price, daily inference spend cap — enforced in code before any money moves.

## Architecture

```
                       config.yaml  (human set constraints: kill switch,
                              │      min price, daily spend cap, splits,
                              │      agent key allowlist)
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
        Claude report   on chain payout     public ledger
        (inference,     contributors 20%    (amount, cost, splits,
         cost logged)   via restricted      tx hash, model, timestamp)
                        function call key
              └───────────────┴──────────────────┘
                              ▼
                    report delivered to customer
```

**Custody model (security track):** payments never touch the agent — 1Click routes settled funds directly to the owner's NEAR account (`recipient`). The agent's signing key is a *function-call access key* on the owner account, restricted by config (`agent_key.allowed_contracts` / `allowed_methods`) to USDC `ft_transfer` only; anything else is rejected before signing. The owner's full-access key is never present in the agent's environment.

## Repository layout

| Path | Purpose |
|---|---|
| `main.py` | FastAPI web app: order API, payment-status polling, QR codes, ledger API, serves the pages |
| `index.html` | Customer page: request, pay, live progress stepper, report delivery |
| `dashboard.html` | Public ledger dashboard with aggregate stats |
| `agentd.py` | CLI daemon for fully automatic fulfillment |
| `demo_mode.py` | Simulated full cycle with no real transactions |
| `payment_demo.py` | Payment receiving demo (quote, deposit address, wait) |
| `demo.py` | End to end order demo |
| `src/payment.py` | 1Click integration: quotes, deposit addresses, status polling |
| `src/agent.py` | Order orchestration: constraints, inference, revenue split, ledger |
| `src/inference.py` | Claude (Anthropic compatible) report generation |
| `src/constraints.py` | Business rules: kill switch, minimum price, daily spend limit |
| `src/config.py` | YAML config loader |
| `src/ledger.py` | Public ledger logging with `/tmp` fallback on read-only filesystems |
| `src/near_tx.py` | NEAR transaction borsh serialization + Ed25519 signing |
| `src/payout.py` | On-chain contributor payouts with allowlist enforcement |
| `src/demo_mode.py` | Simulated order cycle logic |
| `config.yaml` | All settings: price, limits, splits, payment recipient, agent key allowlist |
| `.env.example` | Template for environment variables |
| `tests/` | Test suite (pytest) |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your real keys
. .env
```

Environment variables (see `.env.example`):

| Variable | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | for real reports | Claude-compatible inference key |
| `AGENT_NEAR_PRIVATE_KEY` | for live payouts | agent's restricted function-call key (hex) |
| `OUTLAYER_API_KEY` | optional | reserved for OutLayer custody integration |
| `ZAI_API_KEY` | optional | unused since the Anthropic switch; kept for compatibility |

Never commit real keys. `.env` is gitignored. On Vercel, keys go in **Settings → Environment Variables** instead. Demo mode needs no keys at all.

Key `config.yaml` settings:

| Setting | Purpose |
|---|---|
- `price_usd` — standard report price (currently `1.0`)
- `min_price_usd` — reject orders below this
- `max_daily_inference_spend_usd` — daily inference budget
- `revenue_split` — owner / contributors / reserve shares
- `recipient` / `refund_to` — your NEAR account for settled payments and refunds
- `payment_deadline_minutes` — quote expiry (currently 10)
- `split.contributors_account` — where the 20% contributors share is paid
- `agent_key` — the agent's restricted key allowlist (its spend authority)
- `kill_switch` — set `true` to pause all order acceptance instantly

## Usage

### Web app (customer facing)

```bash
uvicorn main:app --reload
# open http://localhost:8000
```

API endpoints:

- `POST /api/order` — `{"topic": "...", "demo": false}` → order ID + deposit address + amount
- `GET /api/order/{id}` — current status; generates the report automatically once payment settles
- `GET /api/qr/{id}` — payment QR (SVG) encoding the deposit address and exact amount
- `GET /api/ledger` — public ledger entries
- `GET /dashboard` — public ledger dashboard page

### CLI daemon (fully automatic)

```bash
python agentd.py request "Any research topic" 1.0   # get payment details
python agentd.py                                    # daemon: poll payments, auto deliver
python agentd.py status                             # inspect orders
```

### Demo mode (no funds, no keys)

```bash
python demo_mode.py "Any topic" 1.0
```

Simulates the entire cycle: constraints check, instant settlement on a fake `SIMULATED` deposit address, report, and 70/20/10 split. Every output and ledger entry is marked SIMULATED. The web page has a **Try demo** button for the same flow.

### Other demos

```bash
python demo.py            # one real order end to end
python payment_demo.py    # quote and deposit address only (--no-wait skips waiting)
```

### Creating the agent's restricted key (for live payouts)

1. In a NEAR wallet (Meteor, MyNearWallet, etc.), add a **function-call access key** on the owner account, restricted to the USDC contract and the `ft_transfer` method.
2. Export its private key hex as `AGENT_NEAR_PRIVATE_KEY`.
3. Mirror the same allowlist in `config.yaml` under `agent_key` (defense in depth: the protocol grant and the agent's own pre-signing check must agree).

Without this key the full flow still works. Payouts are recorded as `payout_pending` in the ledger instead of being sent.

## Deploy to Vercel

1. Push the repo to GitHub.
2. On vercel.com: **Add New → Project** → import the repo (Python runtime is auto-detected; `main.py` exports the `app`).
3. Add environment variable `ANTHROPIC_API_KEY` (Settings → Environment Variables).
4. Disable **Deployment Protection → Vercel Authentication** for production so visitors can reach the API.
5. Deploy. The site serves the customer page, dashboard, and order API.

### Deployment notes

- **Order state is ephemeral** on serverless (stored in `/tmp`, per-instance). Fine for a demo; use a database (e.g., Vercel KV/Postgres) for production.
- Report generation runs inside the status-polling request after settlement, so no separate worker is needed on Vercel.
- The `agentd.py` daemon is for local/self-hosted use; Vercel serverless cannot run long-lived polling loops.
- The ledger falls back to `/tmp` when the filesystem is read-only, so orders never fail on logging.

## How payment detection works

1. `src/payment.py` requests a quote from `1click.chaindefuser.com` (`POST /v0/quote`) with `depositType: INTENTS` — the response contains a unique deposit address and exact input amount.
2. The customer sends the exact amount to that address from any supported chain. Cross-chain routing is handled by the solvers.
3. `GET /v0/status?depositAddress=...` is polled until the status is `SETTLED`, `EXPIRED`, or `REFUNDED`.
4. On `SETTLED`, the order proceeds to report generation. Refunds/expirations are recorded and reported as `payment_failed`.

## Revenue split

- **owner** 70% — you
- **contributors** 20% (paid on-chain when the agent key is configured)
- **reserve** 10%

Every order (amount, inference cost, splits, report preview, model used, timestamp, payout tx hash) is appended to `public_ledger.json` and shown on `/dashboard`.

## Safety and guardrails

- `kill_switch: true` in `config.yaml` pauses all order acceptance instantly.
- Minimum price and daily inference spend limits are enforced by `src/constraints.py`.
- The agent's signing capability is allowlisted twice: at the NEAR protocol level (function-call key grant) and again in `src/payout.py` before any transaction is signed.
- The API key is read from the environment only — never commit keys.

## Tests

```bash
pytest tests/
```
