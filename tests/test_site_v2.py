import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test")

from unittest.mock import patch

from fastapi.testclient import TestClient

import main


def test_default_price_is_one_dollar(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ORDERS_FILE", tmp_path / "orders.json")
    c = TestClient(main.app)
    o = c.post("/api/order", json={"topic": "t"}).json()
    assert o["amount_usd"] == 1.0


def test_qr_endpoint_returns_svg(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ORDERS_FILE", tmp_path / "orders.json")
    c = TestClient(main.app)
    o = c.post("/api/order", json={"topic": "t"}).json()
    q = c.get(f"/api/qr/{o['order_id']}")
    assert q.status_code == 200
    assert q.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in q.content


def test_dashboard_and_ledger_api(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ORDERS_FILE", tmp_path / "orders.json")
    c = TestClient(main.app)
    assert c.get("/dashboard").status_code == 200
    r = c.get("/api/ledger").json()
    assert "entries" in r
