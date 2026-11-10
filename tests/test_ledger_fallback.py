import pathlib

import src.ledger as L


def test_log_sale_falls_back_to_tmp(monkeypatch):
    monkeypatch.setattr(L, "LEDGER_FILE", pathlib.Path("/proc/nope/ledger.json"))
    L.log_sale({"type": "TEST"})
    assert pathlib.Path("/tmp/public_ledger.json").exists()
