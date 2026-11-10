import uuid
from src.config import load_config
from src.constraints import check_constraints, record_spend
from src.inference import generate_report
from src.ledger import log_sale
from src.payout import split_revenue


def process_order(topic: str, payment_amount_usd: float, payment_token: str = "USDC") -> dict:
    """
    Full order flow:
        1. Check constraints
        2. Generate report
        3. Calculate revenue split
        4. Log to public ledger
    """
    cfg = load_config()

    # Step 1: Check rules
    ok, reason = check_constraints(payment_amount_usd)
    if not ok:
        return {
            "status": "rejected",
            "reason": reason
        }

    # Step 2: Generate the report
    try:
        report, inference_cost = generate_report(topic)
        record_spend(inference_cost)
    except Exception as e:
        return {
            "status": "error",
            "reason": f"Inference failed: {str(e)}"
        }

    # Step 3: Calculate splits
    split = cfg.get("revenue_split", {})
    owner_share = payment_amount_usd * split.get("owner", 0.70)
    contributors_share = payment_amount_usd * split.get("contributors", 0.20)
    reserve = payment_amount_usd * split.get("reserve", 0.10)

    # Step 4: Create order record
    order_id = str(uuid.uuid4())[:8]

    log_entry = {
        "order_id": order_id,
        "topic": topic,
        "amount_usd": payment_amount_usd,
        "token": payment_token,
        "inference_cost_usd": round(inference_cost, 6),
        "owner_share": round(owner_share, 4),
        "contributors_share": round(contributors_share, 4),
        "reserve": round(reserve, 4),
        "model_used": cfg.get("model", "glm-5.3"),
        "report_preview": report[:250] + "..." if len(report) > 250 else report
    }

    log_sale(log_entry)

    # Step 5: on-chain payout of the contributors share (restricted agent key)
    try:
        payout = split_revenue(log_entry)
    except Exception as e:
        payout = {"payout": "failed", "reason": str(e)}

    return {
        "status": "success",
        "order_id": order_id,
        "report": report,
        "inference_cost_usd": round(inference_cost, 6),
        "splits": {
            "owner": round(owner_share, 4),
            "contributors": round(contributors_share, 4),
            "reserve": round(reserve, 4)
        },
        "payout": payout
    }
