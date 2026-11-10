from unittest.mock import patch

from src.agent import process_order


def test_order_includes_payout_field():
    with patch("src.agent.generate_report", return_value=("R", 0.01)), \
         patch("src.agent.split_revenue", return_value={"payout": "sent", "tx_hash": "abc"}), \
         patch("src.agent.log_sale"):
        r = process_order("t", 8.0)
    assert r["payout"] == {"payout": "sent", "tx_hash": "abc"}


def test_order_survives_payout_failure():
    with patch("src.agent.generate_report", return_value=("R", 0.01)), \
         patch("src.agent.split_revenue", side_effect=Exception("rpc down")), \
         patch("src.agent.log_sale"):
        r = process_order("t", 8.0)
    assert r["payout"]["payout"] == "failed"
