from flask import Blueprint, jsonify, request

from ..db import db
from ..models.order import Order
from ..models.customer import Customer
from ..models.charge import Charge
from ..models.payment import PaymentApplication
from ..models.order_item import OrderItem
from ..models.purchase import Purchase
from ..models.purchase_allocation import PurchaseAllocation
from ..models.variant import VariantPriceTier
from ..models.catalog_price import CatalogPrice


accounting_bp = Blueprint("accounting", __name__)


def _sum_billed(charges: list[Charge]) -> float:
    return sum(max(0.0, (c.total or 0.0) - (c.discount_amount or 0.0)) for c in charges)


def _sum_paid_for_charge_ids(charge_ids: list[int]) -> float:
    if not charge_ids:
        return 0.0
    apps = PaymentApplication.query.filter(PaymentApplication.charge_id.in_(charge_ids)).all()
    return sum(a.amount or 0.0 for a in apps)


@accounting_bp.get("/accounting/orders")
def orders_summary():
    """
    Resumen de contabilidad por pedido.
    
    Lógica simplificada:
    1. FACTURADO = suma de (charged_qty × sale_unit_price) de cada OrderItem
       - charged_qty es la cantidad en la unidad de cobro (actualizada en compras)
       - sale_unit_price es el precio por unidad de cobro (guardado en pedidos)
    
    2. COSTO = suma de price_total de cada Purchase
    
    3. COMPRADO/FALTANTE = comparación de cantidades pedidas vs compradas
    """
    orders = Order.query.order_by(Order.created_at.desc()).limit(200).all()
    result = []
    
    for o in orders:
        # Obtener items del pedido
        items = OrderItem.query.filter_by(order_id=o.id).all()
        
        # Obtener compras del pedido
        purchases = Purchase.query.filter_by(order_id=o.id).all()
        
        # ===== 1. CÁLCULO DE FACTURADO =====
        # Facturado total: suma de (charged_qty × sale_unit_price) por cada item
        billed_total = 0.0
        billed_by_customer = {}
        
        for item in items:
            # Cantidad a cobrar: usar charged_qty si está disponible, si no usar qty
            qty_to_bill = item.charged_qty if item.charged_qty is not None else float(item.qty or 0.0)
            
            # Precio de venta por unidad de cobro
            unit_price = float(item.sale_unit_price or 0.0)
            
            # Monto facturado para este item
            item_billed = qty_to_bill * unit_price
            billed_total += item_billed
            
            # Acumular por cliente
            customer_id = item.customer_id
            billed_by_customer[customer_id] = billed_by_customer.get(customer_id, 0.0) + item_billed
        
        # ===== 2. CÁLCULO DE COSTO =====
        total_cost = 0.0
        for purchase in purchases:
            if purchase.price_total is not None:
                total_cost += float(purchase.price_total or 0.0)
            else:
                # Si no hay price_total, calcular desde price_per_unit × cantidad en charged_unit
                unit = purchase.charged_unit or "kg"
                qty = float(purchase.qty_kg or 0.0) if unit == "kg" else float(purchase.qty_unit or 0.0)
                total_cost += float(purchase.price_per_unit or 0.0) * qty
        
        # ===== 3. ESTADO DE COMPRA (completo/incompleto/exceso) =====
        # Cantidades necesarias por producto (según lo pedido)
        needed_by_product = {}
        for item in items:
            pid = item.product_id
            unit = item.unit or "kg"
            if pid not in needed_by_product:
                needed_by_product[pid] = {"kg": 0.0, "unit": 0.0}
            needed_by_product[pid][unit] = needed_by_product[pid].get(unit, 0.0) + float(item.qty or 0.0)
        
        # Cantidades compradas por producto
        purchased_by_product = {}
        for purchase in purchases:
            pid = purchase.product_id
            if pid not in purchased_by_product:
                purchased_by_product[pid] = {"kg": 0.0, "unit": 0.0}
            
            # Sumar kg comprados (incluyendo equivalencia)
            if purchase.qty_kg:
                purchased_by_product[pid]["kg"] += float(purchase.qty_kg or 0.0)
            if purchase.eq_qty_kg is not None:
                purchased_by_product[pid]["kg"] += float(purchase.eq_qty_kg or 0.0)
            
            # Sumar unidades compradas (incluyendo equivalencia)
            if purchase.qty_unit:
                purchased_by_product[pid]["unit"] += float(purchase.qty_unit or 0.0)
            if purchase.eq_qty_unit is not None:
                purchased_by_product[pid]["unit"] += float(purchase.eq_qty_unit or 0.0)
        
        # Determinar estado (complete/incomplete/over)
        status = "complete"
        has_excess = False
        bought_tags = []
        missing_tags = []
        
        for pid, needed in needed_by_product.items():
            purchased = purchased_by_product.get(pid, {"kg": 0.0, "unit": 0.0})
            
            need_kg = float(needed.get("kg", 0.0) or 0.0)
            need_unit = float(needed.get("unit", 0.0) or 0.0)
            got_kg = float(purchased.get("kg", 0.0) or 0.0)
            got_unit = float(purchased.get("unit", 0.0) or 0.0)
            
            # Verificar si está completo
            kg_ok = (need_kg == 0 or got_kg >= need_kg)
            unit_ok = (need_unit == 0 or got_unit >= need_unit)
            
            if not (kg_ok and unit_ok):
                status = "incomplete"
            
            # Verificar si hay exceso
            if (need_kg > 0 and got_kg > need_kg) or (need_unit > 0 and got_unit > need_unit):
                has_excess = True
            
            # Tags de comprado/faltante
            if got_kg > 0 or got_unit > 0:
                bought_tags.append({"product_id": pid, "kg": got_kg, "unit": got_unit})
            
            missing_kg = max(0.0, need_kg - got_kg)
            missing_unit = max(0.0, need_unit - got_unit)
            if missing_kg > 0 or missing_unit > 0:
                missing_tags.append({"product_id": pid, "kg": missing_kg, "unit": missing_unit})
        
        if status == "complete" and has_excess:
            status = "over"
        
        # ===== 4. PAGADO =====
        charges = Charge.query.filter(Charge.order_id == o.id).all()
        charge_ids = [c.id for c in charges]
        paid = _sum_paid_for_charge_ids(charge_ids)
        
        # ===== 5. RESULTADO =====
        profit_amount = max(0.0, billed_total - total_cost)
        profit_pct = (profit_amount / billed_total * 100.0) if billed_total > 0 else 0.0
        
        result.append({
            "order": o.to_dict(),
            "billed": billed_total,
            "paid": paid,
            "due": max(0.0, billed_total - paid),
            "purchase_status": status,
            "cost": total_cost,
            "profit_amount": profit_amount,
            "profit_pct": profit_pct,
            "bought_money": 0.0,  # No usado en frontend
            "missing_money": 0.0,  # No usado en frontend
            "bought_tags": bought_tags,
            "missing_tags": missing_tags,
            "billed_by_customer": billed_by_customer,
        })
    
    return jsonify(result)


@accounting_bp.get("/accounting/customers")
def customers_summary():
    """
    Resumen de contabilidad por cliente.
    
    Usa charged_qty del Charge (que se actualiza cuando se registra la compra)
    para calcular correctamente el monto facturado considerando conversiones.
    """
    include_orders = bool((request.args.get("include_orders") or "").strip().lower() in ("1","true","yes"))
    customers = Customer.query.order_by(Customer.name.asc()).all()
    result = []
    for c in customers:
        charges = Charge.query.filter(Charge.customer_id == c.id).all()
        
        # Calcular facturado usando charged_qty (que incluye conversiones) si está disponible
        billed = 0.0
        for ch in charges:
            qty_to_charge = ch.charged_qty if ch.charged_qty is not None else float(ch.qty or 0.0)
            billed += max(0.0, (qty_to_charge * float(ch.unit_price or 0.0)) - (ch.discount_amount or 0.0))
        
        charge_ids = [ch.id for ch in charges]
        paid = _sum_paid_for_charge_ids(charge_ids)
        
        row = {
            "customer": c.to_dict(),
            "billed": billed,
            "paid": paid,
            "due": max(0.0, billed - paid),
        }
        
        if include_orders:
            orders = {}
            for ch in charges:
                o = orders.setdefault(ch.order_id or 0, {"order_id": ch.order_id, "billed": 0.0, "paid": 0.0})
                # Usar charged_qty para el cálculo por pedido también
                qty_to_charge = ch.charged_qty if ch.charged_qty is not None else float(ch.qty or 0.0)
                o["billed"] += max(0.0, (qty_to_charge * float(ch.unit_price or 0.0)) - (ch.discount_amount or 0.0))
            
            apps = PaymentApplication.query.filter(PaymentApplication.charge_id.in_(charge_ids)).all() if charge_ids else []
            paid_by_charge = {}
            for a in apps:
                paid_by_charge[a.charge_id] = (paid_by_charge.get(a.charge_id) or 0.0) + (a.amount or 0.0)
            for ch in charges:
                orders[ch.order_id or 0]["paid"] += paid_by_charge.get(ch.id, 0.0)
            row["orders"] = list(orders.values())
        
        result.append(row)
    return jsonify(result)



