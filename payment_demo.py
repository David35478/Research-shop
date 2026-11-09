"""Payment-receiving demo using NEAR Intents 1Click.

Flow: customer pays -> agent detects the payment -> generates report -> splits revenue.
Run it and send the printed deposit address the quoted USDC amount; the script
will pick up the settlement and produce the order.
"""
import json
import os
import sys

from src.payment import get_quote, wait_for_settlement, run_paid_order


TOPIC = "Current adoption of NEAR Intents"
AMOUNT_USD = 8.0


def main():
    quote = get_quote(AMOUNT_USD)
    print(json.dumps({
        "step": "awaiting_payment",
        "deposit_address": quote["depositAddress"],
        "amount_in_usd": quote.get("amountInUsd"),
        "send_amount_base_units": quote.get("amountIn"),
        "time_estimate_s": quote.get("timeEstimate"),
        "note": "Send the quoted amount to this address, then the agent detects the payment",
    }, indent=2))

    if "--no-wait" in sys.argv:
        return

    settlement = wait_for_settlement(quote["depositAddress"], timeout_s=int(os.getenv("PAYMENT_WAIT_S", "900")))
    print(json.dumps({"step": "payment_detected", "status": settlement.get("status")}, indent=2))

    if settlement.get("status") != "SETTLED":
        sys.exit(1)

    result = run_paid_order(TOPIC, AMOUNT_USD)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
