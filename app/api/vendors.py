from flask import Blueprint, jsonify, request

from ..db import db
from ..models.vendor import Vendor
from .auth import require_token


vendors_bp = Blueprint("vendors", __name__)


@vendors_bp.get("/vendors")
def list_vendors():
    items = Vendor.query.order_by(Vendor.name.asc()).all()
    return jsonify([v.to_dict() for v in items])


@vendors_bp.post("/vendors")
@require_token
def create_vendor():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    v = Vendor(name=name, notes=data.get("notes"))
    db.session.add(v)
    db.session.commit()
    return jsonify(v.to_dict()), 201


@vendors_bp.put("/vendors/<int:vendor_id>")
@require_token
def update_vendor(vendor_id: int):
    v = Vendor.query.get_or_404(vendor_id)
    data = request.get_json(silent=True) or {}
    if data.get("name"):
        v.name = data.get("name").strip()
    if "notes" in data:
        v.notes = data.get("notes")
    db.session.commit()
    return jsonify(v.to_dict())



