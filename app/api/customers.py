from flask import Blueprint, jsonify, request
from ..db import db
from ..models.customer import Customer
from .auth import require_token

customers_bp = Blueprint("customers", __name__)


@customers_bp.get("/customers")
@require_token
def list_customers():
    """Lista clientes. Los vendedores solo ven sus propios clientes."""
    user = getattr(request, 'current_user', None)
    
    query = Customer.query
    
    # Si es vendedor, filtrar solo sus clientes
    if user and user.role == 'vendor':
        query = query.filter(Customer.vendor_id == user.id)
    
    items = query.order_by(Customer.name.asc()).all()
    return jsonify([c.to_dict() for c in items])


@customers_bp.post("/customers")
@require_token
def create_customer():
    """Crea un nuevo cliente. Los vendedores automáticamente lo asignan a sí mismos."""
    user = getattr(request, 'current_user', None)
    
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    if not name or not phone:
        return jsonify({"error": "name and phone are required"}), 400
    
    # Determinar vendor_id
    vendor_id = data.get("vendor_id")
    if user.role == 'vendor':
        # Los vendedores solo pueden crear clientes asignados a ellos mismos
        vendor_id = user.id
    elif vendor_id:
        # Los admins pueden especificar un vendor_id
        vendor_id = int(vendor_id)
    else:
        # Admin puede dejar sin asignar (None)
        vendor_id = None
    
    c = Customer(
        name=name,
        phone=phone,
        rut=(data.get("rut") or None),
        nickname=(data.get("nickname") or None),
        preferences=(data.get("preferences") or None),
        personality=(data.get("personality") or None),
        address=(data.get("address") or None),
        email=(data.get("email") or None),
        vendor_id=vendor_id,
    )
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201
