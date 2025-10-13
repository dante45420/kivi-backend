from flask import Blueprint, jsonify, request

from ..db import db
from ..models.purchase import Purchase
from ..models.price_history import PriceHistory
from ..models.catalog_price import CatalogPrice
from ..models.order_item import OrderItem
from ..models.inventory import InventoryLot
from .auth import require_token
from ..models.purchase_allocation import PurchaseAllocation

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

    # Crear lote de inventario para sobrantes (solo la diferencia que excede lo requerido)
    try:
        order_id = data.get("order_id")
        if order_id:
            items = OrderItem.query.filter_by(order_id=order_id, product_id=product_id).all()
            need_kg = sum((it.qty or 0) for it in items if (it.unit or "kg") == "kg")
            need_unit = sum((it.qty or 0) for it in items if (it.unit or "kg") == "unit")
            got_prev = Purchase.query.filter_by(order_id=order_id, product_id=product_id).all()
            prev_kg = sum((x.qty_kg or 0) for x in got_prev[:-1]) if got_prev else 0.0
            prev_unit = sum((x.qty_unit or 0) for x in got_prev[:-1]) if got_prev else 0.0
            buy_kg = float(p.qty_kg or 0.0)
            buy_unit = float(p.qty_unit or 0.0)
            # excedente atribuible a esta compra
            rem_kg_before = max(0.0, (need_kg or 0.0) - (prev_kg or 0.0))
            rem_unit_before = max(0.0, (need_unit or 0.0) - (prev_unit or 0.0))
            extra_kg = max(0.0, buy_kg - rem_kg_before)
            extra_unit = max(0.0, buy_unit - rem_unit_before)
            if extra_kg > 0 or extra_unit > 0:
                db.session.add(InventoryLot(product_id=product_id, source_purchase_id=p.id, order_id=order_id, qty_kg=(extra_kg or None), qty_unit=(extra_unit or None), status="unassigned"))
                db.session.commit()
        else:
            # compras fuera de pedido: todo es excedente asignable
            if (p.qty_kg or 0) or (p.qty_unit or 0):
                db.session.add(InventoryLot(product_id=product_id, source_purchase_id=p.id, order_id=None, qty_kg=p.qty_kg, qty_unit=p.qty_unit, status="unassigned"))
                db.session.commit()
    except Exception:
        pass
    # Asignar automáticamente a clientes si se indican (CSV/lista) en compras incompletas
    try:
        order_id = data.get("order_id")
        raw_customers = data.get("customers")
        cust_list = []
        if isinstance(raw_customers, list):
            cust_list = [c.strip() for c in raw_customers if (c or "").strip()]
        elif isinstance(raw_customers, str):
            cust_list = [c.strip() for c in raw_customers.split(',') if c.strip()]
        if order_id and cust_list:
            # OrderItems de esos clientes para este producto
            q_items = OrderItem.query.filter(OrderItem.order_id == order_id, OrderItem.product_id == product_id)
            items = [it for it in q_items.all() if (it.customer_id and (it.unit or "kg") == charged_unit)]
            # Map customer_id -> pendiente
            pending = {}
            for it in items:
                bought_prev = 0.0
                # calcular asignado previo
                alloc_prev = PurchaseAllocation.query.join(OrderItem, PurchaseAllocation.order_item_id == OrderItem.id).filter(OrderItem.id == it.id).all()
                bought_prev = sum(a.qty or 0.0 for a in alloc_prev)
                need = max(0.0, float(it.qty or 0.0) - bought_prev)
                if need > 0:
                    pending[it.customer_id] = pending.get(it.customer_id, 0.0) + need
            # distribuir la compra actual en orden del listado de clientes
            remain = float(p.qty_kg if charged_unit=='kg' else p.qty_unit or 0.0)
            for name in cust_list:
                if remain <= 0: break
                # buscar OrderItem del cliente por nombre
                # nota: por simplicidad, buscar por nombre actual en draft_detail no disponible aquí; asumimos coincidencia por cantidad pendiente
                for it in items:
                    if pending.get(it.customer_id, 0.0) <= 0:
                        continue
                    take = min(remain, pending[it.customer_id])
                    if take > 0:
                        db.session.add(PurchaseAllocation(purchase_id=p.id, order_item_id=it.id, qty=take, unit=charged_unit))
                        pending[it.customer_id] -= take
                        remain -= take
            db.session.commit()
    except Exception:
        pass
    # Auto-asignar si la compra completa el producto (sin necesidad de especificar clientes)
    try:
        order_id = data.get("order_id")
        if order_id:
            # Solo para la unidad cobrada
            q_items = OrderItem.query.filter(OrderItem.order_id == order_id, OrderItem.product_id == product_id, OrderItem.unit == charged_unit)
            items = q_items.all()
            if items:
                # calcular pendiente previo a esta compra por item
                pending_by_item = {}
                total_pending = 0.0
                for it in items:
                    alloc_prev = PurchaseAllocation.query.filter(PurchaseAllocation.order_item_id == it.id).all()
                    bought_prev = sum(float(a.qty or 0.0) for a in alloc_prev)
                    need = max(0.0, float(it.qty or 0.0) - bought_prev)
                    if need > 0:
                        pending_by_item[it.id] = need
                        total_pending += need
                purchased_now = float(p.qty_kg if charged_unit == 'kg' else p.qty_unit or 0.0)
                if purchased_now >= total_pending and total_pending > 0:
                    remain = total_pending
                    for it in items:
                        need = pending_by_item.get(it.id, 0.0)
                        if need <= 0:
                            continue
                        take = min(need, remain)
                        if take > 0:
                            db.session.add(PurchaseAllocation(purchase_id=p.id, order_item_id=it.id, qty=take, unit=charged_unit))
                            remain -= take
                            if remain <= 0:
                                break
                    db.session.commit()
    except Exception:
        pass
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
    except Exception as e:
        # Log error pero no bloquear la compra
        print(f"Error actualizando charged_qty: {e}")
        pass
    return jsonify(p.to_dict()), 201
