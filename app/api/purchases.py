from flask import Blueprint, jsonify, request
from datetime import datetime

from ..db import db
from ..models.purchase import Purchase
from ..models.price_history import PriceHistory
from ..models.catalog_price import CatalogPrice
from ..models.order_item import OrderItem
from .auth import require_token

purchases_bp = Blueprint("purchases", __name__)


@purchases_bp.get("/purchases")
def list_purchases():
    items = Purchase.query.order_by(Purchase.created_at.desc()).limit(200).all()
    return jsonify([p.to_dict() for p in items])


@purchases_bp.post("/purchases")
@require_token
def create_purchase():
    data = request.get_json(silent=True) or {}
    # Validaciones mínimas
    try:
        product_id = int(data.get("product_id") or 0)
    except (TypeError, ValueError):
        product_id = 0
    try:
        price_per_unit = float(data.get("price_per_unit")) if data.get("price_per_unit") is not None else None
    except (TypeError, ValueError):
        price_per_unit = None
    charged_unit = (data.get("charged_unit") or None)
    if not product_id:
        return jsonify({"error": "product_id is required"}), 400
    if price_per_unit is None or price_per_unit <= 0:
        return jsonify({"error": "price_per_unit (costo) es obligatorio y debe ser > 0"}), 400
    if not charged_unit:
        return jsonify({"error": "charged_unit es obligatorio (kg o unit)"}), 400
    p = Purchase(
        order_id=data.get("order_id"),
        product_id=product_id,
        qty_kg=data.get("qty_kg"),
        qty_unit=data.get("qty_unit"),
        charged_unit=charged_unit,
        price_total=data.get("price_total"),
        price_per_unit=price_per_unit,
        vendor=(data.get("vendor") or "Lo Valledor"),
        notes=data.get("notes"),
        customers=(",".join(data.get("customers") or []) if isinstance(data.get("customers"), list) else data.get("customers")),
    )
    # guardar monto facturado esperado si viene
    try:
        if data.get("billed_expected") is not None:
            p.billed_expected = float(data.get("billed_expected") or 0.0)
    except Exception:
        pass
    db.session.add(p)
    # Guardar equivalencias si vienen (para evitar suposiciones de 1 a 1)
    try:
        eq_kg = data.get("eq_qty_kg"); eq_unit = data.get("eq_qty_unit")
        if eq_kg is not None: p.eq_qty_kg = float(eq_kg)
        if eq_unit is not None: p.eq_qty_unit = float(eq_unit)
    except Exception:
        pass
    # Validar clientes obligatorios si la compra NO completa la cantidad requerida del producto
    try:
        order_id = data.get("order_id")
        if order_id:
            items = OrderItem.query.filter_by(order_id=order_id, product_id=product_id).all()
            need_kg = sum((it.qty or 0) for it in items if (it.unit or "kg") == "kg")
            need_unit = sum((it.qty or 0) for it in items if (it.unit or "kg") == "unit")
            # Comprado hasta ahora (previo a commit) + actual
            got_prev = Purchase.query.filter_by(order_id=order_id, product_id=product_id).all()
            got_kg = sum((x.qty_kg or 0) for x in got_prev) + float(data.get("qty_kg") or 0)
            got_unit = sum((x.qty_unit or 0) for x in got_prev) + float(data.get("qty_unit") or 0)
            completes = ((need_kg == 0 or got_kg >= need_kg) and (need_unit == 0 or got_unit >= need_unit))
            if not completes:
                raw_customers = data.get("customers")
                has_customers = False
                if isinstance(raw_customers, list):
                    has_customers = any((c or "").strip() for c in raw_customers)
                else:
                    has_customers = bool(((raw_customers or "").strip()))
                if not has_customers:
                    return jsonify({"error": "customers are required when product is not fully purchased"}), 400
    except Exception:
        # En caso de error de cálculo, no bloquear
        pass

    # Guardar precio histórico automático: costo y venta actual
    current_sale = None
    try:
        c = (
            CatalogPrice.query.filter(CatalogPrice.product_id == product_id)
            .order_by(CatalogPrice.date.desc())
            .first()
        )
        current_sale = c.sale_price if c else None
    except Exception:
        current_sale = None
    ph = PriceHistory(product_id=product_id, cost=price_per_unit, sale=current_sale, unit=charged_unit)
    db.session.add(ph)
    db.session.commit()
    # Actualizar charged_qty en OrderItem según conversión observada en esta compra
    # Este es el paso crítico para que la contabilidad funcione correctamente
    try:
        order_id = data.get("order_id")
        if order_id:
            from ..models.order_item import OrderItem as _OI
            
            # Calcular ratio de conversión unidades/kg desde esta compra
            ratio_units_per_kg = None
            
            # Caso 1: Se cobra en kg y se compraron unidades (eq_qty_kg es cuántos kg representan las unidades compradas)
            if charged_unit == 'kg':
                qty_unit_bought = float(p.qty_unit or 0.0)
                eq_kg = float(p.eq_qty_kg or 0.0) if p.eq_qty_kg is not None else 0.0
                if qty_unit_bought > 0 and eq_kg > 0:
                    ratio_units_per_kg = qty_unit_bought / eq_kg
            
            # Caso 2: Se cobra en unidades y se compraron kg (eq_qty_unit es cuántas unidades representan los kg comprados)
            elif charged_unit == 'unit':
                qty_kg_bought = float(p.qty_kg or 0.0)
                eq_unit = float(p.eq_qty_unit or 0.0) if p.eq_qty_unit is not None else 0.0
                if qty_kg_bought > 0 and eq_unit > 0:
                    ratio_units_per_kg = eq_unit / qty_kg_bought
            
            # Actualizar todos los order items del producto en este pedido
            items = _OI.query.filter(_OI.order_id == order_id, _OI.product_id == product_id).all()
            for it in items:
                it.charged_unit = charged_unit
                
                # Si la unidad pedida coincide con la de cobro, no hay conversión
                if (it.unit or 'kg') == charged_unit:
                    it.charged_qty = float(it.qty or 0.0)
                # Si hay conversión y tenemos ratio, aplicarlo
                elif ratio_units_per_kg and ratio_units_per_kg > 0:
                    qty_original = float(it.qty or 0.0)
                    if charged_unit == 'kg' and (it.unit or 'kg') == 'unit':
                        # Cliente pidió unidades, se cobra en kg
                        it.charged_qty = qty_original / ratio_units_per_kg
                    elif charged_unit == 'unit' and (it.unit or 'kg') == 'kg':
                        # Cliente pidió kg, se cobra en unidades
                        it.charged_qty = qty_original * ratio_units_per_kg
                    else:
                        # Caso no manejado, dejar qty original como fallback
                        it.charged_qty = qty_original
                else:
                    # Sin ratio disponible, usar qty original como fallback
                    # Esto puede pasar si solo se compró en una unidad sin conversión
                    it.charged_qty = float(it.qty or 0.0)
            
            db.session.commit()
            
            # Actualizar también los Charges correspondientes con la nueva charged_qty
            from ..models.charge import Charge as _Charge
            for it in items:
                charges = _Charge.query.filter(_Charge.order_item_id == it.id).all()
                for charge in charges:
                    # Actualizar charged_qty y recalcular total
                    charge.charged_qty = it.charged_qty
                    qty_to_charge = charge.charged_qty if charge.charged_qty is not None else float(charge.qty or 0.0)
                    charge.total = qty_to_charge * float(charge.unit_price or 0.0)
            
            db.session.commit()
    except Exception:
        # Error actualizando charged_qty, no bloquear la compra
        pass
    return jsonify(p.to_dict()), 201


@purchases_bp.patch('/purchases/<int:purchase_id>/quantity')
@require_token
def update_purchase_quantity(purchase_id):
    """Actualizar la cantidad comprada de una compra"""
    purchase = Purchase.query.get_or_404(purchase_id)
    data = request.get_json() or {}
    
    qty_kg = data.get('qty_kg')
    qty_unit = data.get('qty_unit')
    
    if qty_kg is not None:
        purchase.qty_kg = float(qty_kg)
    if qty_unit is not None:
        purchase.qty_unit = float(qty_unit)
    
    # Recalcular precio_per_unit si hay price_total
    if purchase.price_total and (purchase.qty_kg or purchase.qty_unit):
        if purchase.charged_unit == 'kg' and purchase.qty_kg:
            purchase.price_per_unit = purchase.price_total / purchase.qty_kg
        elif purchase.charged_unit == 'unit' and purchase.qty_unit:
            purchase.price_per_unit = purchase.price_total / purchase.qty_unit
    
    db.session.commit()
    return jsonify(purchase.to_dict())


@purchases_bp.patch('/purchases/<int:purchase_id>/charged_unit')
@require_token
def update_purchase_charged_unit(purchase_id):
    """Actualizar la unidad de cobro de una compra"""
    purchase = Purchase.query.get_or_404(purchase_id)
    data = request.get_json() or {}
    
    charged_unit = data.get('charged_unit')
    if charged_unit not in ['kg', 'unit']:
        return jsonify({"error": "charged_unit debe ser 'kg' o 'unit'"}), 400
    
    purchase.charged_unit = charged_unit
    
    # Recalcular precio_per_unit basado en la nueva unidad
    if purchase.price_total:
        if charged_unit == 'kg' and purchase.qty_kg:
            purchase.price_per_unit = purchase.price_total / purchase.qty_kg
        elif charged_unit == 'unit' and purchase.qty_unit:
            purchase.price_per_unit = purchase.price_total / purchase.qty_unit
    
    # Actualizar OrderItems correspondientes
    try:
        if purchase.order_id and purchase.product_id:
            from ..models.order_item import OrderItem as _OI
            items = _OI.query.filter(
                _OI.order_id == purchase.order_id,
                _OI.product_id == purchase.product_id
            ).all()
            
            for it in items:
                it.charged_unit = charged_unit
                # Recalcular charged_qty según la nueva unidad
                if (it.unit or 'kg') == charged_unit:
                    it.charged_qty = float(it.qty or 0.0)
            
            # Actualizar Charges
            from ..models.charge import Charge as _Charge
            for it in items:
                charges = _Charge.query.filter(_Charge.order_item_id == it.id).all()
                for charge in charges:
                    charge.charged_qty = it.charged_qty
                    qty_to_charge = charge.charged_qty if charge.charged_qty is not None else float(charge.qty or 0.0)
                    charge.total = qty_to_charge * float(charge.unit_price or 0.0)
    except Exception:
        pass
    
    db.session.commit()
    return jsonify(purchase.to_dict())


@purchases_bp.delete('/purchases/<int:purchase_id>')
@require_token
def delete_purchase(purchase_id):
    """Eliminar una compra (útil para corregir duplicados)"""
    purchase = Purchase.query.get_or_404(purchase_id)
    
    try:
        # Eliminar la compra
        db.session.delete(purchase)
        db.session.commit()
        
        return jsonify({"message": "Compra eliminada exitosamente"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
