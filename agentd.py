"""Automatic agent worker.

Runs a continuous loop: takes queued orders (topic + amount), requests a
1Click quote, waits for the customer's deposit, then generates the report
and splits revenue -- no manual steps.

Usage:
    python agentd.py                  # run the daemon
    python agentd.py enqueue "topic" 8.0   # queue an order
    python agentd.py status           # show all orders
"""
import json
import sys
import threading
import time
from pathlib import Path

from src.payment import get_quote, settle_and_fulfill

ORDERS_FILE = Path("orders.json")
_lock = threading.Lock()


def load_orders() -> list:
    if ORDERS_FILE.exists():
        return json.loads(ORDERS_FILE.read_text())
    return []


def save_orders(orders: list):
    with _lock:
        ORDERS_FILE.write_text(json.dumps(orders, indent=2))


def enqueue(topic: str, amount_usd: float) -> dict:
    orders = load_orders()
    order = {
        "order_id": f"o{len(orders) + 1}",
        "topic": topic,
        "amount_usd": amount_usd,
        "status": "quoted",
    }
    quote = get_quote(amount_usd)
    order["deposit_address"] = quote["depositAddress"]
    order["amount_in_usd"] = quote.get("amountInUsd")
    order["send_amount_base_units"] = quote.get("amountIn")
    order["time_estimate_s"] = quote.get("timeEstimate")
    orders.append(order)
    save_orders(orders)
    print(json.dumps({"queued": order}, indent=2))
    return order


def run_loop(poll_s: int = 15):
    print("agentd: watching for payments...", flush=True)
    while True:
        orders = load_orders()
        changed = False
        for order in orders:
            if order.get("status") == "quoted":
                changed = True
                print(f"agentd: order {order['order_id']} awaiting payment at {order['deposit_address']}", flush=True)
                result = settle_and_fulfill(order)
                order.update(result)
                print(f"agentd: order {order['order_id']} -> {order.get('status')} "
                      f"(payment: {order.get('payment_state')})", flush=True)
                save_orders(orders)
        if not changed:
            time.sleep(poll_s)


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "enqueue":
        enqueue(sys.argv[2], float(sys.argv[3]))
    elif len(sys.argv) >= 2 and sys.argv[1] == "status":
        print(json.dumps(load_orders(), indent=2))
    else:
        run_loop()


if __name__ == "__main__":
    main()
