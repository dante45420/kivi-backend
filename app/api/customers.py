from flask import Blueprint, jsonify, request
from ..db import db
from ..models.customer import Customer

customers_bp = Blueprint("customers", __name__)


@customers_bp.get("/customers")
def list_customers():
    """Lista clientes. Los vendedores solo ven sus propios clientes."""
    # Retrocompatibilidad: funciona con o sin autenticación
    user = getattr(request, 'current_user', None)
    
    query = Customer.query
    
    # Si es vendedor, filtrar solo sus clientes
    if user and user.role == 'vendor':
        query = query.filter(Customer.vendor_id == user.id)
    
    items = query.order_by(Customer.name.asc()).all()
    return jsonify([c.to_dict() for c in items])


@customers_bp.post("/customers")
def create_customer():
    """Crea un nuevo cliente. Los vendedores automáticamente lo asignan a sí mismos."""
    # Retrocompatibilidad: funciona con o sin autenticación
    user = getattr(request, 'current_user', None)
    
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    if not name or not phone:
        return jsonify({"error": "name and phone are required"}), 400
    
    # Determinar vendor_id
    vendor_id = data.get("vendor_id")
    if user and user.role == 'vendor':
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


@customers_bp.patch("/customers/<int:customer_id>")
def update_customer(customer_id):
    """Actualiza un cliente existente."""
    data = request.get_json(silent=True) or {}
    
    customer = Customer.query.get_or_404(customer_id)
    
    # Actualizar campos permitidos
    if "name" in data:
        customer.name = data["name"].strip() if data["name"] else None
    if "phone" in data:
        customer.phone = data["phone"].strip() if data["phone"] else None
    if "rut" in data:
        customer.rut = data["rut"].strip() if data["rut"] else None
    if "nickname" in data:
        customer.nickname = data["nickname"].strip() if data["nickname"] else None
    if "preferences" in data:
        customer.preferences = data["preferences"].strip() if data["preferences"] else None
    if "personality" in data:
        customer.personality = data["personality"].strip() if data["personality"] else None
    if "address" in data:
        customer.address = data["address"].strip() if data["address"] else None
    if "email" in data:
        customer.email = data["email"].strip() if data["email"] else None
    
    db.session.commit()
    return jsonify(customer.to_dict())


@customers_bp.delete("/customers/<int:customer_id>")
def delete_customer(customer_id):
    """Elimina un cliente."""
    customer = Customer.query.get_or_404(customer_id)
    db.session.delete(customer)
    db.session.commit()
    return jsonify({"message": "Cliente eliminado correctamente"}), 200
