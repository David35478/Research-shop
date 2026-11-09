"""Fully automatic agent worker.

Lifecycle:
    1. Customer requests a report -> unique order ID + payment address + amount
    2. Customer sends the payment
    3. Agent polls 1Click until the payment is detected
    4. Agent generates the report
    5. Agent logs everything, applies the revenue split, and saves the report

Usage:
    python agentd.py request "topic" 8.0   # customer request -> payment details
    python agentd.py                       # daemon: poll payments, auto-deliver
    python agentd.py status                # show all orders
"""
import uuid
import json
import sys
import threading
import time
from pathlib import Path

from src.payment import get_quote, wait_for_settlement
from src.agent import process_order

ORDERS_FILE = Path("orders.json")
REPORTS_DIR = Path("reports")
_lock = threading.Lock()
_lock = threading.Lock()


def load_orders() -> list:
    if ORDERS_FILE.exists():
        return json.loads(ORDERS_FILE.read_text())
    return []


def save_orders(orders: list):
    with _lock:
        ORDERS_FILE.write_text(json.dumps(orders, indent=2))


def request_report(topic: str, amount_usd: float) -> dict:
    orders = load_orders()
    order_id = str(uuid.uuid4())[:8]
    order = {
        "order_id": order_id,
        "topic": topic,
        "amount_usd": amount_usd,
        "status": "awaiting_payment",
    }
    quote = get_quote(amount_usd)
    order["deposit_address"] = quote["depositAddress"]
    order["amount_in_usd"] = quote.get("amountInUsd")
    order["send_amount_base_units"] = quote.get("amountIn")
    order["time_estimate_s"] = quote.get("timeEstimate")
    orders.append(order)
    save_orders(orders)
    print(json.dumps({
        "step": "request_accepted",
        "order_id": order_id,
        "pay": {
            "deposit_address": quote["depositAddress"],
            "amount_usd": quote.get("amountInUsd"),
            "send_amount_base_units": quote.get("amountIn"),
            "time_estimate_s": quote.get("timeEstimate"),
        },
        "note": "Send the exact amount to this address; the agent will detect it and deliver the report automatically",
    }, indent=2))
    return order


def fulfill(order: dict) -> dict:
    """Poll for the payment, then generate + log + save the report."""
    settlement = wait_for_settlement(order["deposit_address"])
    order["payment_state"] = settlement.get("status")
    if settlement.get("status") != "SETTLED":
        order["status"] = "payment_failed"
        save_orders(load_orders())
        return order

    order["status"] = "payment_detected"
    save_orders(load_orders())

    result = process_order(order["topic"], order["amount_usd"])
    order.update(result)

    # Deliver the report as a file the customer can pick up
    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = REPORTS_DIR / f"{order['order_id']}.md"
    report_path.write_text(
        f"# Report: {order['topic']}\n\n"
        f"Order: {order['order_id']}  |  Paid: ${order['amount_usd']}  |  "
        f"Payment state: {settlement.get('status')}\n\n"
        f"{result.get('report', '')}\n"
    )
    order["report_path"] = str(report_path)
    order["status"] = result.get("status", "delivered")
    save_orders(load_orders())
    return order


def run_loop(poll_s: int = 15):
    print("agentd: polling for payments...", flush=True)
    while True:
        orders = load_orders()
        for order in orders:
            if order.get("status") == "awaiting_payment":
                print(f"agentd: order {order['order_id']} polling {order['deposit_address']}", flush=True)
                fulfill(order)
                print(f"agentd: order {order['order_id']} -> {order.get('status')} "
                      f"(payment: {order.get('payment_state')}, report: {order.get('report_path')})", flush=True)
                save_orders(load_orders())
        time.sleep(poll_s)


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "enqueue":
        request_report(sys.argv[2], float(sys.argv[3]))
    elif len(sys.argv) >= 2 and sys.argv[1] == "request":
        request_report(sys.argv[2], float(sys.argv[3]))
    elif len(sys.argv) >= 2 and sys.argv[1] == "status":
        print(json.dumps(load_orders(), indent=2))
    else:
        run_loop()


if __name__ == "__main__":
    main()
