import os
from unittest.mock import patch

os.environ.setdefault("ANTHROPIC_API_KEY", "test")

from fastapi.testclient import TestClient

import main


def test_order_settled_delivers_report(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ORDERS_FILE", tmp_path / "orders.json")
    client = TestClient(main.app)
    r = client.post("/api/order", json={"topic": "t", "amount_usd": 8.0})
    oid = r.json()["order_id"]
    with patch("main.get_status", return_value={"status": "SETTLED"}), \
         patch("main.process_order", return_value={"status": "success", "report": "R", "order_id": oid, "splits": {}}):
        o = client.get(f"/api/order/{oid}").json()
    assert o["status"] == "success"
    assert o["report"] == "R"
