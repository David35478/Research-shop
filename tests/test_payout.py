import os
from unittest.mock import patch

from src.near_tx import encode_function_call_tx, decode_function_call_tx, sign_transaction
from src.payout import _agent_key_conf, _check_allowance, split_revenue, build_ft_transfer


def test_tx_roundtrip():
    tx = encode_function_call_tx(
        "david354.near", "aa" * 32, 77, "usdc.token.near", "bb" * 32,
        "ft_transfer", b'{"amount":"1600000"}', 30000000000000, 1,
    )
    d = decode_function_call_tx(tx)
    assert d["signer_id"] == "david354.near"
    assert d["method_name"] == "ft_transfer"
    assert d["deposit"] == 1
    assert d["gas"] == 30000000000000
    assert d["args"] == b'{"amount":"1600000"}'


def test_signature_verifies():
    sk = os.urandom(32).hex()
    tx = encode_function_call_tx("a.near", "aa" * 32, 1, "b.near", "bb" * 32, "ft_transfer", b"{}", 1, 0)
    signed = sign_transaction(tx, sk)
    import base64
    raw = base64.b64decode(signed["signed_tx"])
    assert raw[:len(tx)] == tx  # signature appended after tx bytes


def test_allowance_blocks_other_contracts():
    conf = {"allowed_contracts": ["usdc"], "allowed_methods": ["ft_transfer"]}
    import pytest
    with pytest.raises(PermissionError):
        _check_allowance(conf, "other.token.near", "ft_transfer")
    with pytest.raises(PermissionError):
        _check_allowance(conf, "usdc", "withdraw")


def test_split_revenue_pending_without_key(tmp_path, monkeypatch):
    monkeypatch.setenv("PAYOUT_TEST_KEY", "")
    monkeypatch.setattr("src.payout.RPC", "unused")
    order = {"order_id": "o1", "contributors_share": 1.6}
    with patch("src.payout.log_sale"), patch("src.payout.load_config", return_value={"split": {}, "agent_key": {"env": "PAYOUT_TEST_KEY"}}):
        r = split_revenue(order)
    assert r["payout"] == "pending"


def test_split_revenue_sends_payout_with_key(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_NEAR_PRIVATE_KEY", os.urandom(32).hex())
    cfg = {
        "split": {"contributors_account": "pool.near", "token_contract": "usdc"},
        "agent_key": {"env": "AGENT_NEAR_PRIVATE_KEY", "account": "david354.near",
                      "allowed_contracts": ["usdc"], "allowed_methods": ["ft_transfer"]},
    }
    order = {"order_id": "o1", "contributors_share": 1.6}
    with patch("src.payout.load_config", return_value=cfg), \
         patch("src.payout.log_sale") as ls, \
         patch("src.payout._fetch_access_key_nonce", return_value=99), \
         patch("src.payout._recent_block_hash", return_value="cc" * 32), \
         patch("src.payout._submit", return_value={"result": {"status": {"SuccessValue": ""}}}) as sub:
        r = split_revenue(order)
    assert r["payout"] == "sent"
    entry = ls.call_args[0][0]
    assert entry["type"] == "payout" and entry["to"] == "pool.near" and entry["amount"] == 1600000
    built = sub.call_args[0][0]["signedTx"]
    import base64
    raw = base64.b64decode(built)
    d = decode_function_call_tx(raw[: -1 - 32 - 64])
    assert d["receiver_id"] == "usdc" and d["method_name"] == "ft_transfer"
    import json
    args = json.loads(d["args"])
    assert args == {"receiver_id": "pool.near", "amount": "1600000", "memo": "research-shop:o1"}
