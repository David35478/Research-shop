# Research Shop

**A one person AI research firm.** A single autonomous agent sells short market, tech, and crypto reports. It accepts payment in any token via NEAR Intents, buys its own inference, pays its contributors on chain, and obeys hard human set constraints. Humans write the rules in a config file. The agent runs the company.

## Try it in two minutes

1. Open the deployed site, or run `uvicorn main:app` locally.
2. Type a topic, then click **Try demo (simulated, no payment)** to see the full cycle with zero risk.
3. For the real flow, click **Buy report** and send 1 USDC to the deposit address shown (a QR code is displayed for wallet apps).
4. The page detects the payment, Claude writes the report, and the report renders in place.
5. Revenue splits 70% owner, 20% contributors, 10% compute reserve. The contributors share is paid on chain. Every order is logged publicly.

Quotes expire in 10 minutes and unclaimed deposits refund automatically.

## Why this wins

1. **Company of one.** The agent sells, produces, pays suppliers (inference), pays staff (contributors), and keeps books (ledger). Humans only set guardrails in `config.yaml`.
2. **Real economic loop.** Payments settle through live 1Click solvers. Payouts are real NEAR `ft_transfer` transactions. Every step is auditable in `public_ledger.json`.
3. **Security by custody design.** The agent never holds the owner's full access key. It signs with its own function call access key, allowlisted in config to exactly one contract and one method, revocable from any NEAR wallet.
4. **Human control.** Kill switch, minimum price, and daily inference spend cap are enforced in code before any money moves.

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

**Custody model.** Payments never touch the agent. 1Click routes settled funds directly to the owner's NEAR account (`recipient`). The agent's signing key is a function call access key on the owner account, restricted by config (`agent_key.allowed_contracts` and `agent_key.allowed_methods`) to USDC `ft_transfer` only. Anything else is rejected before signing. The owner's full access key is never present in the agent's environment.

## Repository layout

| Path | Purpose |
|---|---|
| `main.py` | FastAPI web app: order API, payment status polling, QR codes, ledger API, serves the pages |
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
| `src/ledger.py` | Public ledger logging with `/tmp` fallback on read only filesystems |
| `src/near_tx.py` | NEAR transaction borsh serialization and Ed25519 signing |
| `src/payout.py` | On chain contributor payouts with allowlist enforcement |
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
| `ANTHROPIC_API_KEY` | for real reports | Claude compatible inference key |
| `AGENT_NEAR_PRIVATE_KEY` | for live payouts | agent's restricted function call key (hex) |
| `OUTLAYER_API_KEY` | optional | reserved for OutLayer custody integration |
| `ZAI_API_KEY` | optional | unused since the Anthropic switch; kept for compatibility |

Never commit real keys. `.env` is gitignored. On Vercel, keys go in **Settings → Environment Variables** instead. Demo mode needs no keys at all.

Key `config.yaml` settings:

| Setting | Purpose |
|---|---|
| `price_usd` | standard report price (currently `1.0`) |
| `min_price_usd` | reject orders below this |
| `max_daily_inference_spend_usd` | daily inference budget |
| `revenue_split` | owner / contributors / reserve shares |
| `recipient`, `refund_to` | your NEAR account for settled payments and refunds |
| `payment_deadline_minutes` | quote expiry (currently 10) |
| `split.contributors_account` | where the 20% contributors share is paid |
| `agent_key` | the agent's restricted key allowlist (its spend authority) |
| `kill_switch` | set `true` to pause all order acceptance instantly |

## Usage

### Web app (customer facing)

```bash
uvicorn main:app --reload
# open http://localhost:8000
```

API endpoints:

| Endpoint | Purpose |
|---|---|
| `POST /api/order` | create an order; returns order id, deposit address, amount |
| `GET /api/order/{id}` | payment status; generates the report once settled |
| `GET /api/qr/{id}` | payment QR (SVG) encoding the deposit address and amount |
| `GET /api/ledger` | public ledger entries |
| `GET /dashboard` | public ledger dashboard page |

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

1. In a NEAR wallet (Meteor, MyNearWallet, and similar), add a **function call access key** on the owner account, restricted to the USDC contract and the `ft_transfer` method.
2. Export its private key hex as `AGENT_NEAR_PRIVATE_KEY`.
3. Mirror the same allowlist in `config.yaml` under `agent_key` (defense in depth: the protocol grant and the agent's own pre signing check must agree).

Without this key the full flow still works. Payouts are recorded as `payout_pending` in the ledger instead of being sent.

## Deploy to Vercel

1. Push the repo to GitHub.
2. On vercel.com: **Add New → Project**, import the repo (Python runtime is auto detected; `main.py` exports the `app`).
3. Add environment variable `ANTHROPIC_API_KEY` in **Settings → Environment Variables**.
4. Disable **Deployment Protection → Vercel Authentication** for production so visitors can reach the API.
5. Deploy. The site serves the customer page, dashboard, and order API.

### Deployment notes

1. Order state is ephemeral on serverless (stored in `/tmp`, per instance). Fine for a demo; use a database (Vercel KV or Postgres) for production.
2. Report generation runs inside the status polling request after settlement, so no separate worker is needed on Vercel.
3. The `agentd.py` daemon is for local or self hosted use. Vercel serverless cannot run long lived polling loops.
4. The ledger falls back to `/tmp` when the filesystem is read only, so orders never fail on logging.

## How payment detection works

1. `src/payment.py` requests a quote from `1click.chaindefuser.com` (`POST /v0/quote`) with `depositType: INTENTS`. The response contains a unique deposit address and exact input amount.
2. The customer sends the exact amount to that address from any supported chain. Cross chain routing is handled by the solvers.
3. `GET /v0/status?depositAddress=...` is polled until the status is `SETTLED`, `EXPIRED`, or `REFUNDED`.
4. On `SETTLED`, the order proceeds to report generation. Refunds and expirations are recorded and reported as `payment_failed`.

## Revenue split

Each successful order is split per `config.yaml`:

1. **owner** 70%
2. **contributors** 20% (paid on chain when the agent key is configured)
3. **reserve** 10%

Every order (amount, inference cost, splits, report preview, model used, timestamp, payout tx hash) is appended to `public_ledger.json` and shown on `/dashboard`.

## Safety and guardrails

1. `kill_switch: true` in `config.yaml` pauses all order acceptance instantly.
2. Minimum price and daily inference spend limits are enforced by `src/constraints.py`.
3. The agent's signing capability is allowlisted twice: at the NEAR protocol level (function call key grant) and again in `src/payout.py` before any transaction is signed.
4. API keys are read from the environment only. Never commit keys.

## Tests

```bash
pytest tests/
```
