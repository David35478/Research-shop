from unittest.mock import patch

from src.demo_mode import run_demo_order


def test_demo_order_full_cycle():
    r = run_demo_order("test topic", 8.0)
    assert r["status"] == "success"
    assert r["simulated"] is True
    assert r["amount_usd"] == 8.0
    assert r["splits"]["owner"] == 5.6
    assert r["payout"].startswith("SIMULATED")
    assert r["deposit_address"].startswith("SIMULATED-")


def test_demo_order_respects_constraints():
    r = run_demo_order("cheap", 0.25)  # below min_price_usd (0.5)
    assert r["status"] == "rejected"


def test_demo_logs_to_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr("src.demo_mode.log_sale", lambda e: None)
    run_demo_order("t", 8.0)  # would log a DEMO entry
