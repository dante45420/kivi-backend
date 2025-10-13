from flask import Blueprint, jsonify, request

from ..db import db
from ..models.inventory import InventoryLot, ProcessingRecord
from ..models.product import Product
from ..models.order import Order
from .auth import require_token


inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.get("/inventory/lots")
def list_lots():
    product_id = request.args.get("product_id", type=int)
    only_unassigned = True
    q = InventoryLot.query
    if product_id:
        q = q.filter(InventoryLot.product_id == product_id)
    if only_unassigned:
        q = q.filter(InventoryLot.status == "unassigned")
    rows = q.order_by(InventoryLot.created_at.desc()).limit(500).all()
    result = []
    for r in rows:
        d = r.to_dict()
        try:
            prod = Product.query.get(r.product_id)
            d["product_name"] = prod.name if prod else None
        except Exception:
            d["product_name"] = None
        try:
            ord = Order.query.get(r.order_id) if r.order_id else None
            d["order_title"] = ord.title if ord else None
            d["order_date"] = (ord.created_at.isoformat() if ord and ord.created_at else None)
        except Exception:
            d["order_title"] = None
            d["order_date"] = None
        result.append(d)
    return jsonify(result)


@inventory_bp.post("/inventory/lots")
@require_token
def create_lot():
    data = request.get_json(silent=True) or {}
    lot = InventoryLot(
        product_id=int(data.get("product_id")),
        source_purchase_id=data.get("source_purchase_id"),
        qty_kg=data.get("qty_kg"),
        qty_unit=data.get("qty_unit"),
        status=(data.get("status") or "unassigned"),
        notes=data.get("notes"),
    )
    db.session.add(lot)
    db.session.commit()
    return jsonify(lot.to_dict()), 201


@inventory_bp.post("/inventory/process")
@require_token
def process_lot():
    data = request.get_json(silent=True) or {}
    rec = ProcessingRecord(
        from_product_id=int(data.get("from_product_id")),
        to_product_id=int(data.get("to_product_id")),
        input_qty_kg=float(data.get("input_qty_kg") or 0),
        output_qty=float(data.get("output_qty") or 0),
        unit=(data.get("unit") or "unit"),
        yield_percent=data.get("yield_percent"),
        cost_transferred=data.get("cost_transferred"),
    )
    db.session.add(rec)
    db.session.commit()
    return jsonify(rec.to_dict()), 201


