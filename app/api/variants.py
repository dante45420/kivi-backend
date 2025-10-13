from flask import Blueprint, jsonify, request

from ..db import db
from ..models.variant import ProductVariant, VariantPriceTier
from .auth import require_token


variants_bp = Blueprint("variants", __name__)


@variants_bp.get("/variants")
def list_variants():
    product_id = request.args.get("product_id", type=int)
    q = ProductVariant.query
    if product_id:
        q = q.filter(ProductVariant.product_id == product_id)
    rows = q.order_by(ProductVariant.label.asc()).all()
    return jsonify([r.to_dict() for r in rows])


@variants_bp.post("/variants")
@require_token
def create_variant():
    data = request.get_json(silent=True) or {}
    v = ProductVariant(product_id=int(data.get("product_id")), label=(data.get("label") or "").strip(), active=bool(data.get("active") if data.get("active") is not None else True))
    db.session.add(v)
    db.session.commit()
    return jsonify(v.to_dict()), 201


@variants_bp.put("/variants/<int:variant_id>")
@require_token
def update_variant(variant_id: int):
    data = request.get_json(silent=True) or {}
    v = ProductVariant.query.get_or_404(variant_id)
    if "label" in data:
        v.label = (data.get("label") or v.label)
    if data.get("active") is not None:
        v.active = bool(data.get("active"))
    db.session.commit()
    return jsonify(v.to_dict())


@variants_bp.get("/variants/tiers")
def list_tiers():
    product_id = request.args.get("product_id", type=int)
    variant_id = request.args.get("variant_id", type=int)
    q = VariantPriceTier.query
    if product_id:
        q = q.filter(VariantPriceTier.product_id == product_id)
    if variant_id:
        q = q.filter(VariantPriceTier.variant_id == variant_id)
    rows = q.order_by(VariantPriceTier.min_qty.asc()).all()
    return jsonify([r.to_dict() for r in rows])


@variants_bp.post("/variants/tiers")
@require_token
def create_tier():
    data = request.get_json(silent=True) or {}
    t = VariantPriceTier(product_id=int(data.get("product_id")), variant_id=(int(data.get("variant_id")) if data.get("variant_id") else None), min_qty=float(data.get("min_qty") or 1.0), unit=(data.get("unit") or "kg"), sale_price=float(data.get("sale_price") or 0))
    db.session.add(t)
    db.session.commit()
    return jsonify(t.to_dict()), 201


