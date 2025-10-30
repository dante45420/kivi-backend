from flask import Blueprint, jsonify, request

from ..db import db
from ..models.charge import Charge
from ..models.order_item import OrderItem
from .auth import require_token


charges_bp = Blueprint("charges", __name__)


@charges_bp.get("/charges")
def list_charges():
    customer_id = request.args.get("customer_id", type=int)
    order_id = request.args.get("order_id", type=int)
    status = request.args.get("status")
    q = Charge.query
    if customer_id:
        q = q.filter(Charge.customer_id == customer_id)
    if order_id:
        q = q.filter(Charge.order_id == order_id)
    if status:
        q = q.filter(Charge.status == status)
    rows = q.order_by(Charge.created_at.desc()).limit(500).all()
    return jsonify([c.to_dict() for c in rows])


@charges_bp.post("/charges")
@require_token
def create_charge():
    data = request.get_json(silent=True) or {}

    # Datos base
    customer_id = int(data.get("customer_id"))
    order_id = data.get("order_id")
    original_order_id = data.get("original_order_id")
    order_item_id = data.get("order_item_id")
    product_id = int(data.get("product_id"))
    qty = float(data.get("qty") or 0)
    unit = (data.get("unit") or "kg")
    unit_price = float(data.get("unit_price") or 0)
    discount_amount = float(data.get("discount_amount") or 0)
    discount_reason = (data.get("discount_reason") or None)
    status = (data.get("status") or "pending")

    charged_qty = data.get("charged_qty")

    # Si viene order_item_id, usar la conversión registrada en el OrderItem
    try:
        if order_item_id and charged_qty is None:
            oi = OrderItem.query.get(order_item_id)
            if oi:
                # Tomar charged_qty y unidad de cobro del ítem si existen
                if oi.charged_qty is not None:
                    charged_qty = float(oi.charged_qty or 0.0)
                unit = oi.charged_unit or oi.unit or unit
    except Exception:
        pass

    # Calcular total consistente
    qty_to_charge = float(charged_qty) if charged_qty is not None else float(qty or 0.0)
    total = qty_to_charge * unit_price

    c = Charge(
        customer_id=customer_id,
        order_id=order_id,
        original_order_id=original_order_id,
        order_item_id=order_item_id,
        product_id=product_id,
        qty=qty,
        charged_qty=charged_qty,
        unit=unit,
        unit_price=unit_price,
        discount_amount=discount_amount,
        discount_reason=discount_reason,
        total=total,
        status=status,
    )
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201


@charges_bp.post("/charges/reassign-excess")
@require_token
def reassign_excess():
    """
    Reasignar excedente creando un nuevo OrderItem en la orden original
    Esto mantiene el cálculo de excedentes simple: comprado - pedido
    """
    data = request.get_json(silent=True) or {}
    
    # Validar datos requeridos
    required_fields = ["order_id", "product_id", "customer_id", "qty", "unit", "unit_price"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"Campo requerido: {field}"}), 400
    
    order_id = int(data.get("order_id"))
    product_id = int(data.get("product_id"))
    customer_id = int(data.get("customer_id"))
    qty = float(data.get("qty"))
    unit = data.get("unit")
    unit_price = float(data.get("unit_price"))
    
    try:
        # Crear nuevo OrderItem en la orden original
        order_item = OrderItem(
            order_id=order_id,
            product_id=product_id,
            customer_id=customer_id,
            qty=qty,
            unit=unit,
            charged_qty=qty,  # Mismo que qty para simplicidad
            charged_unit=unit,  # Mismo que unit para simplicidad
        )
        
        db.session.add(order_item)
        db.session.flush()  # Para obtener el ID del order_item
        
        # Crear el Charge correspondiente
        charge = Charge(
            customer_id=customer_id,
            order_id=order_id,
            order_item_id=order_item.id,
            product_id=product_id,
            qty=qty,
            unit=unit,
            charged_qty=qty,
            unit_price=unit_price,
            total=qty * unit_price,
            status="pending"
        )
        
        db.session.add(charge)
        db.session.commit()
        
        return jsonify({
            "message": "Excedente reasignado correctamente",
            "order_item": order_item.to_dict(),
            "charge": charge.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error al reasignar excedente: {str(e)}"}), 500


