"""Web app for the research shop demo.

    POST /api/order        -> create order, return payment details
    GET  /api/order/{id}   -> payment status; generates report once settled
    GET  /                 -> customer page
"""
import json
import uuid
import io
import base64
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
import qrcode
import qrcode.image.svg

from src.payment import get_quote, get_status
from src.agent import process_order
from src.demo_mode import run_demo_order
from src.ledger import get_ledger
from src.config import load_config

app = FastAPI(title="Research Shop")
ORDERS_FILE = Path("/tmp/orders_web.json")


class OrderRequest(BaseModel):
    topic: str
    amount_usd: float | None = None
    demo: bool = False


def load_orders() -> dict:
    if ORDERS_FILE.exists():
        return json.loads(ORDERS_FILE.read_text())
    return {}


def save_orders(orders: dict):
    ORDERS_FILE.write_text(json.dumps(orders, indent=2))


@app.post("/api/order")
def create_order(req: OrderRequest):
    cfg = load_config()
    amount = req.amount_usd if req.amount_usd is not None else cfg.get("price_usd", 1.0)
    try:
        if req.demo:
            return run_demo_order(req.topic, amount)
    except Exception as e:
        raise HTTPException(500, f"demo order failed: {e}")
    order_id = str(uuid.uuid4())[:8]
    quote = get_quote(amount)
    order = {
        "order_id": order_id,
        "topic": req.topic,
        "amount_usd": amount,
        "status": "awaiting_payment",
        "deposit_address": quote["depositAddress"],
        "amount_in_usd": quote.get("amountInUsd"),
        "send_amount_base_units": quote.get("amountIn"),
    }
    orders = load_orders()
    orders[order_id] = order
    save_orders(orders)
    return order


@app.get("/api/qr/{order_id}")
def order_qr(order_id: str):
    """Payment QR: encodes the exact deposit address + amount for wallet apps."""
    order = load_orders().get(order_id)
    if not order:
        raise HTTPException(404, "order not found")
    data = f"{order['deposit_address']}|amount={order['send_amount_base_units']}"
    img = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage, box_size=12)
    buf = io.BytesIO()
    img.save(buf)
    return Response(
        content=buf.getvalue(),
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/dashboard")
def dashboard():
    return FileResponse("dashboard.html")


@app.get("/api/ledger")
def ledger_public():
    entries = [e for e in get_ledger() if e.get("type") != "payout_pending"]
    return {"entries": entries}


@app.get("/api/order/{order_id}")
def order_status(order_id: str):
    order = load_orders().get(order_id)
    if not order:
        raise HTTPException(404, "order not found")
    if order["status"] in ("awaiting_payment",):
        settlement = get_status(order["deposit_address"])
        state = settlement.get("status")
        if state == "SETTLED":
            order["status"] = "payment_detected"
            result = process_order(order["topic"], order["amount_usd"])
            order.update(result)
        else:
            order["payment_state"] = state
        save_orders(load_orders() | {order_id: order})
    return order


@app.get("/")
def index():
    return FileResponse("index.html")