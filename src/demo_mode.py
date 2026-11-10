"""Demo mode: simulates a full order cycle without any real transaction.

Everything is marked SIMULATED in the ledger and output:
- payment: instant SETTLED on a fake deposit address
- inference: template report, cost estimate only
- payout: recorded, not sent on-chain
"""
import json
import uuid
import time
from datetime import datetime, timezone

from src.config import load_config
from src.constraints import check_constraints, record_spend
from src.ledger import log_sale


SIM_REPORT = """# Research Brief: {topic}

> DEMO MODE — simulated report for demonstration. No payment was taken,
> no inference was purchased, and no funds moved.

## Summary
This simulated brief demonstrates the full company-of-one loop for "{topic}":
payment acceptance, report production, revenue split, and public-ledger
accounting.

## Key points
1. Payment accepted via NEAR Intents (simulated settlement).
2. Report generated (simulated inference; real mode uses Claude).
3. Revenue split applied per config.yaml.
4. Everything logged to public_ledger.json.

## Splits (simulated)
- owner / contributors / reserve per the configured revenue_split.
"""


def run_demo_order(topic: str, amount_usd: float = 8.0) -> dict:
    """Full simulated cycle: constraints -> payment -> report -> split -> ledger."""
    cfg = load_config()

    # 1. Same hard constraints as the real flow
    ok, reason = check_constraints(amount_usd)
    if not ok:
        return {"status": "rejected", "reason": reason, "simulated": True}

    # 2. Simulated payment: instant settlement on a fake deposit address
    deposit_address = "SIMULATED-" + uuid.uuid4().hex[:24]
    estimated_cost = 0.017
    record_spend(estimated_cost)

    # 3. Simulated report
    report = SIM_REPORT.format(topic=topic)

    # 4. Revenue split (same math as the real flow)
    split = cfg.get("revenue_split", {})
    owner_share = amount_usd * split.get("owner", 0.70)
    contributors_share = amount_usd * split.get("contributors", 0.20)
    reserve = amount_usd * split.get("reserve", 0.10)
    order_id = "demo" + str(uuid.uuid4())[:8]

    log_entry = {
        "type": "DEMO",
        "order_id": order_id,
        "topic": topic,
        "amount_usd": amount_usd,
        "simulated": True,
        "deposit_address": deposit_address,
        "payment_state": "SETTLED (SIMULATED)",
        "inference_cost_usd": estimated_cost,
        "owner_share": round(owner_share, 4),
        "contributors_share": round(contributors_share, 4),
        "reserve": round(reserve, 4),
        "payout": "SIMULATED (no on-chain transfer)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "report_preview": report[:250],
    }
    log_sale(log_entry)

    return {
        "status": "success",
        "simulated": True,
        "order_id": order_id,
        "amount_usd": amount_usd,
        "deposit_address": deposit_address,
        "report": report,
        "inference_cost_usd": estimated_cost,
        "splits": {
            "owner": round(owner_share, 4),
            "contributors": round(contributors_share, 4),
            "reserve": round(reserve, 4)
        },
        "payout": "SIMULATED (recorded, not sent)",
    }
