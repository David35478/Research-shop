import os
import time
import requests

from src.agent import process_order
from src.config import load_config

API = "https://1click.chaindefuser.com/v0"


def _token_asset_id(cfg: dict, key: str, chain: str) -> str:
    """Resolve a config entry like 'eth:USDC' or a raw assetId via the token list."""
    if cfg.get(key):
        return cfg[key]
    tokens = requests.get(f"{API}/tokens", timeout=10).json()
    for t in tokens:
        if t["blockchain"] == chain and t["symbol"] == cfg.get("token", "USDC"):
            return t["assetId"]
    raise ValueError(f"No {cfg.get('token', 'USDC')} asset found on chain {chain}")


def get_quote(amount_usd: float, source_chain: str = "eth", dest_chain: str = "near") -> dict:
    """
    Request a 1Click quote for the order amount.
    Returns the quote dict containing depositAddress, amountIn and amountOut.
    """
    cfg = load_config()
    decimals = 6
    amount_base = str(int(round(amount_usd * 10 ** decimals)))
    deadline = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 3600))

    body = {
        "dry": False,
        "originAsset": _token_asset_id(cfg, "payment_source_asset", source_chain),
        "destinationAsset": _token_asset_id(cfg, "payment_dest_asset", dest_chain),
        "amount": amount_base,
        "swapType": "EXACT_INPUT",
        "depositType": "INTENTS",
        "recipient": cfg.get("recipient", "demo.near"),
        "recipientType": "INTENTS",
        "refundType": "INTENTS",
        "refundTo": cfg.get("refund_to", "demo.near"),
        "slippageTolerance": 100,
        "deadline": deadline,
    }
    r = requests.post(f"{API}/quote", json=body, timeout=30)
    r.raise_for_status()
    return r.json()["quote"]


def get_status(deposit_address: str) -> dict:
    r = requests.get(f"{API}/status", params={"depositAddress": deposit_address}, timeout=10)
    if r.status_code == 404:
        return {"status": "PENDING_DEPOSIT"}
    r.raise_for_status()
    return r.json()


def wait_for_settlement(deposit_address: str, timeout_s: int = 600, poll_s: int = 10) -> dict:
    """
    Poll 1Click until the deposit is settled, expired or refunded.
    Returns the final status response.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = get_status(deposit_address)
        state = status.get("status")
        if state in ("SETTLED", "EXPIRED", "REFUNDED"):
            return status
        time.sleep(poll_s)
    return {"status": "TIMEOUT", "last": status}


def run_paid_order(topic: str, payment_amount_usd: float, source_chain: str = "eth") -> dict:
    """
    Full payment flow:
        1. Get a 1Click quote and a deposit address
        2. Wait for the customer's deposit to settle
        3. Generate the report and split revenue via process_order
    """
    quote = get_quote(payment_amount_usd, source_chain=source_chain)
    deposit_address = quote["depositAddress"]

    settlement = wait_for_settlement(deposit_address)
    if settlement.get("status") != "SETTLED":
        return {
            "status": "payment_failed",
            "payment_state": settlement.get("status"),
            "deposit_address": deposit_address,
            "amount_in_usd": quote.get("amountInUsd"),
        }

    result = process_order(topic, payment_amount_usd)
    result["deposit_address"] = deposit_address
    return result
