from datetime import date
from flask import Blueprint, jsonify, request

from ..db import db
from ..models.vendor_price import VendorPrice
from ..models.vendor import Vendor
from .auth import require_token


vendor_prices_bp = Blueprint("vendor_prices", __name__)


@vendor_prices_bp.get("/vendor-prices")
def list_vendor_prices():
    product_id = request.args.get("product_id", type=int)
    vendor_id = request.args.get("vendor_id", type=int)
    q = VendorPrice.query
    if product_id:
        q = q.filter(VendorPrice.product_id == product_id)
    if vendor_id:
        q = q.filter(VendorPrice.vendor_id == vendor_id)
    rows = q.order_by(VendorPrice.date.desc()).limit(300).all()
    return jsonify([vp.to_dict() for vp in rows])


@vendor_prices_bp.post("/vendor-prices")
@require_token
def create_vendor_price():
    data = request.get_json(silent=True) or {}
    pid = int(data.get("product_id"))
    vid = int(data.get("vendor_id"))
    cost = float(data.get("cost"))
    unit = (data.get("unit") or None)
    d = date.fromisoformat(data.get("date")) if data.get("date") else date.today()
    if not Vendor.query.get(vid):
        return jsonify({"error": "vendor not found"}), 400
    vp = VendorPrice(product_id=pid, vendor_id=vid, cost=cost, unit=unit, date=d)
    db.session.add(vp)
    db.session.commit()
    return jsonify(vp.to_dict()), 201



