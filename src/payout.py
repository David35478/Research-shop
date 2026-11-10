"""Revenue split payouts using the agent's restricted function-call key.

Custody model (Security track): the agent never holds the owner's full key.
It gets its own function-call access key on the owner account, restricted to
transferring the settlement token (USDC) — nothing else. Human rules in
config.yaml bound what it can do; the key can be revoked in any NEAR wallet.
"""
import json
import os
import urllib.request

from src.config import load_config
from src.ledger import log_sale
from src.near_tx import encode_function_call_tx, sign_transaction, tx_hash
from nacl.signing import SigningKey

RPC = "https://rpc.testnet.near.org"


def _agent_key_conf():
    cfg = load_config()
    key = cfg.get("agent_key", {})
    private = os.getenv(key.get("env", "AGENT_NEAR_PRIVATE_KEY"), "")
    if not private:
        return None
    sk = SigningKey(bytes.fromhex(private))
    return {
        "private": private,
        "account": key.get("account"),
        "public_key": sk.verify_key.encode().hex(),
        "allowed_contracts": key.get("allowed_contracts", []),
        "allowed_methods": key.get("allowed_methods", ["ft_transfer"]),
    }


def _check_allowance(conf, receiver_id, method):
    if receiver_id not in conf["allowed_contracts"]:
        raise PermissionError(f"contract {receiver_id} not allowed for agent key")
    if method not in conf["allowed_methods"]:
        raise PermissionError(f"method {method} not allowed for agent key")


def _fetch_access_key_nonce(conf) -> int:
    """Current nonce of the agent's access key (next nonce = current + 1)."""
    body = json.dumps({
        "jsonrpc": "2.0", "id": "x",
        "method": "query",
        "params": {"request_type": "view_access_key", "account_id": conf["account"],
                   "public_key": conf["public_key"], "block_id": "final"},
    }).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return resp["result"]["nonce"] + 1


def _recent_block_hash() -> str:
    body = json.dumps({"jsonrpc": "2.0", "id": "x", "method": "block", "params": {"finality": "final"}}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return resp["result"]["header"]["hash"]


def _submit(signed_tx: dict) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": "x", "method": "broadcast_tx_commit", "params": [signed_tx]}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def build_ft_transfer(conf, token_contract, receiver_account, amount_token: int, memo: str) -> dict:
    """Build and sign an ft_transfer with the agent's restricted key."""
    _check_allowance(conf, token_contract, "ft_transfer")
    args = json.dumps({
        "receiver_id": receiver_account,
        "amount": str(amount_token),
        "memo": memo,
    }).encode()
    tx = encode_function_call_tx(
        signer_id=conf["account"],
        public_key_hex=conf["public_key"],
        nonce=conf["nonce"],
        receiver_id=token_contract,
        block_hash_hex=conf["block_hash"],
        method_name="ft_transfer",
        args=args,
        gas=30 * 10**12,
        deposit_yocto=1,  # ft_transfer requires a 1 yoctoNEAR attached deposit
    )
    signed = sign_transaction(tx, conf["private"])
    return {"tx_hash": tx_hash(tx), "signed_tx": signed["signed_tx"]}


def split_revenue(order: dict) -> dict:
    """
    On-chain payout of the contributors share after a settled order.
    If no agent key is configured, records the split as payout_pending instead.
    """
    cfg = load_config()
    split_cfg = cfg.get("split", {})
    contributors_account = split_cfg.get("contributors_account")
    token_contract = split_cfg.get("token_contract")
    amount = int(round(order["contributors_share"] * 10 ** 6))  # USDC 6 decimals

    conf = _agent_key_conf()
    if not (conf and contributors_account and token_contract):
        entry = {"type": "payout_pending", "order_id": order["order_id"],
                 "contributors_share_usd": order["contributors_share"]}
        log_sale(entry)
        return {"payout": "pending", "reason": "agent_key_not_configured"}

    conf["nonce"] = _fetch_access_key_nonce(conf)
    conf["block_hash"] = _recent_block_hash()
    built = build_ft_transfer(conf, token_contract, contributors_account, amount,
                              f"research-shop:{order['order_id']}")
    result = _submit({"signedTx": built["signed_tx"]})
    entry = {"type": "payout", "order_id": order["order_id"], "to": contributors_account,
             "amount": amount, "tx_hash": built["tx_hash"], "rpc": result}
    log_sale(entry)
    return {"payout": "sent", "tx_hash": built["tx_hash"]}
