from datetime import date
from src.config import load_config

# Simple in-memory daily tracker (good enough for demo)
daily_spend = {
    "date": None,
    "amount": 0.0
}


def check_constraints(price_usd: float, estimated_cost_usd: float = 0.0) -> tuple[bool, str]:
    cfg = load_config()

    # 1. Kill switch
    if cfg.get("kill_switch", False):
        return False, "Kill switch is ON. Agent is paused."

    # 2. Minimum price
    min_price = cfg.get("min_price_usd", 5.0)
    if price_usd < min_price:
        return False, f"Price ${price_usd} is below minimum ${min_price}"

    # 3. Daily inference spend limit
    today = str(date.today())
    if daily_spend["date"] != today:
        daily_spend["date"] = today
        daily_spend["amount"] = 0.0

    max_daily = cfg.get("max_daily_inference_spend_usd", 15.0)
    if daily_spend["amount"] + estimated_cost_usd > max_daily:
        return False, f"Daily inference limit exceeded (${daily_spend['amount']:.4f} / ${max_daily})"

    return True, "OK"


def record_spend(amount_usd: float):
    """Call this after a successful inference"""
    today = str(date.today())
    if daily_spend["date"] != today:
        daily_spend["date"] = today
        daily_spend["amount"] = 0.0
    daily_spend["amount"] += amount_usd


def get_daily_spend() -> float:
    return daily_spend["amount"]
