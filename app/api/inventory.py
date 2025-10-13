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


@inventory_bp.post("/inventory/lots/<int:lot_id>/assign")
@require_token
def assign_lot_to_customer(lot_id):
    """Asignar un lote excedente a un cliente como venta"""
    from ..models.order_item import OrderItem
    from ..models.charge import Charge
    from ..models.catalog_price import CatalogPrice
    from datetime import date
    
    data = request.get_json(silent=True) or {}
    customer_id = data.get("customer_id")
    order_id = data.get("order_id")
    unit_price = data.get("unit_price")
    
    if not customer_id:
        return jsonify({"error": "customer_id requerido"}), 400
    
    lot = InventoryLot.query.get_or_404(lot_id)
    
    # Determinar cantidad y unidad
    qty = lot.qty_unit if lot.qty_unit else lot.qty_kg
    unit = "unit" if lot.qty_unit else "kg"
    charged_qty = qty
    charged_unit = unit
    
    # Obtener precio si no se proporciona
    if not unit_price:
        price = CatalogPrice.query.filter(
            CatalogPrice.product_id == lot.product_id,
            CatalogPrice.date <= date.today()
        ).order_by(CatalogPrice.date.desc()).first()
        unit_price = float(price.sale_price) if price else 0.0
    else:
        unit_price = float(unit_price)
    
    # Crear OrderItem
    order_item = OrderItem(
        customer_id=customer_id,
        order_id=order_id,
        product_id=lot.product_id,
        qty=qty,
        unit=unit,
        charged_qty=charged_qty,
        charged_unit=charged_unit,
        sale_unit_price=unit_price
    )
    db.session.add(order_item)
    db.session.flush()
    
    # Crear Charge
    total = charged_qty * unit_price
    charge = Charge(
        customer_id=customer_id,
        order_id=order_id,
        order_item_id=order_item.id,
        product_id=lot.product_id,
        qty=qty,
        charged_qty=charged_qty,
        unit=charged_unit,
        unit_price=unit_price,
        total=total,
        status="pending"
    )
    db.session.add(charge)
    
    # Marcar lote como asignado
    lot.status = "assigned"
    lot.order_id = order_id
    
    db.session.commit()
    
    return jsonify({
        "order_item": order_item.to_dict(),
        "charge": charge.to_dict(),
        "lot": lot.to_dict()
    }), 201


