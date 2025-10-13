from flask import Blueprint, jsonify, request
from ..db import db

from ..models.customer import Customer

customers_bp = Blueprint("customers", __name__)


@customers_bp.get("/customers")
def list_customers():
    items = Customer.query.order_by(Customer.name.asc()).all()
    return jsonify([c.to_dict() for c in items])


@customers_bp.post("/customers")
def create_customer():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    if not name or not phone:
        return jsonify({"error": "name and phone are required"}), 400
    c = Customer(
        name=name,
        phone=phone,
        rut=(data.get("rut") or None),
        nickname=(data.get("nickname") or None),
        preferences=(data.get("preferences") or None),
        personality=(data.get("personality") or None),
        address=(data.get("address") or None),
        email=(data.get("email") or None),
    )
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201
