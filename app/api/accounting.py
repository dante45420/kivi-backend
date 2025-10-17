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
    
    Query params:
    - include_details=1 : Incluye desglose por cliente y producto
    
    Lógica simplificada:
    1. FACTURADO = suma de charges activos (no cancelados)
    2. COSTO = suma de price_total de cada Purchase
    3. COMPRADO/FALTANTE = comparación de cantidades pedidas vs compradas
    """
    include_details = request.args.get('include_details') == '1'
    orders = Order.query.order_by(Order.created_at.desc()).limit(200).all()
    result = []
    
    for o in orders:
        # Obtener items del pedido
        items = OrderItem.query.filter_by(order_id=o.id).all()
        
        # Obtener compras del pedido
        purchases = Purchase.query.filter_by(order_id=o.id).all()
        
        # ===== 1. CÁLCULO DE FACTURADO =====
        # USAR CHARGES en lugar de OrderItems para tener el monto real facturado (considerando cancelaciones)
        # Usamos SOLO order_id (no original_order_id) para que solo aparezca en el pedido ACTUAL
        charges = Charge.query.filter(
            Charge.order_id == o.id
        ).filter(
            Charge.status != 'cancelled'  # No contar cargos cancelados
        ).all()
        
        billed_total = 0.0
        billed_by_customer = {}
        
        for charge in charges:
            # Cantidad a cobrar
            qty_to_bill = charge.charged_qty if charge.charged_qty is not None else float(charge.qty or 0.0)
            
            # Precio de venta por unidad
            unit_price = float(charge.unit_price or 0.0)
            
            # Monto facturado
            charge_billed = qty_to_bill * unit_price
            billed_total += charge_billed
            
            # Acumular por cliente
            customer_id = charge.customer_id
            billed_by_customer[customer_id] = billed_by_customer.get(customer_id, 0.0) + charge_billed
        
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
        # Usar los mismos charges que se usaron para calcular billed
        charge_ids = [c.id for c in charges]
        paid = _sum_paid_for_charge_ids(charge_ids)
        
        # ===== 5. DETALLES (si se solicita) =====
        customers_detail = []
        if include_details:
            from ..models.customer import Customer
            from ..models.product import Product
            
            # Agrupar charges por cliente
            charges_by_customer = {}
            for charge in charges:
                if charge.customer_id not in charges_by_customer:
                    charges_by_customer[charge.customer_id] = []
                charges_by_customer[charge.customer_id].append(charge)
            
            for customer_id, cust_charges in charges_by_customer.items():
                customer = Customer.query.get(customer_id)
                cust_billed = billed_by_customer.get(customer_id, 0.0)
                
                # Agrupar por producto
                products_detail = []
                charges_by_product = {}
                for charge in cust_charges:
                    if charge.product_id not in charges_by_product:
                        charges_by_product[charge.product_id] = []
                    charges_by_product[charge.product_id].append(charge)
                
                for product_id, prod_charges in charges_by_product.items():
                    product = Product.query.get(product_id)
                    
                    # Sumar cantidad y monto total para este producto
                    total_qty = sum(
                        (c.charged_qty if c.charged_qty is not None else c.qty) 
                        for c in prod_charges
                    )
                    total_billed = sum(
                        (c.charged_qty if c.charged_qty is not None else c.qty) * c.unit_price
                        for c in prod_charges
                    )
                    
                    # Estado de compra del producto
                    purchased = purchased_by_product.get(product_id, {"kg": 0.0, "unit": 0.0})
                    needed = needed_by_product.get(product_id, {"kg": 0.0, "unit": 0.0})
                    
                    # Usar la unidad del primer charge para determinar status
                    unit = prod_charges[0].unit
                    if unit == 'kg':
                        purchase_ok = purchased.get("kg", 0) >= needed.get("kg", 0)
                        has_excess = purchased.get("kg", 0) > needed.get("kg", 0)
                    else:
                        purchase_ok = purchased.get("unit", 0) >= needed.get("unit", 0)
                        has_excess = purchased.get("unit", 0) > needed.get("unit", 0)
                    
                    products_detail.append({
                        "product_id": product_id,
                        "product_name": product.name if product else f"Producto #{product_id}",
                        "qty": total_qty,
                        "unit": unit,
                        "unit_price": prod_charges[0].unit_price,  # Asumimos mismo precio
                        "total_billed": total_billed,
                        "purchase_status": "complete" if purchase_ok else ("over" if has_excess else "incomplete"),
                        "charges": [c.to_dict() for c in prod_charges]
                    })
                
                customers_detail.append({
                    "customer_id": customer_id,
                    "customer_name": customer.name if customer else f"Cliente #{customer_id}",
                    "billed": cust_billed,
                    "products": products_detail
                })
        
        # ===== 6. RESULTADO =====
        profit_amount = max(0.0, billed_total - total_cost)
        profit_pct = (profit_amount / billed_total * 100.0) if billed_total > 0 else 0.0
        
        # Solo incluir pedidos con facturación > 0
        if billed_total > 0:
            row = {
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
            }
            
            if include_details:
                row["customers"] = customers_detail
            
            result.append(row)
    
    return jsonify(result)


@accounting_bp.patch("/charges/<int:charge_id>/price")
def update_charge_price(charge_id):
    """Actualizar el precio unitario de un cargo"""
    from ..models.charge import Charge
    from ..models.order_item import OrderItem
    from ..db import db

    charge = Charge.query.get_or_404(charge_id)
    data = request.get_json() or {}
    new_price = data.get('unit_price')

    if new_price is None:
        return jsonify({"error": "unit_price requerido"}), 400

    charge.unit_price = float(new_price)
    qty_to_charge = charge.charged_qty if charge.charged_qty is not None else float(charge.qty or 0.0)
    charge.total = qty_to_charge * float(charge.unit_price or 0.0)
    
    # TAMBIÉN actualizar el OrderItem relacionado para que el resumen de pedido refleje el nuevo precio
    if charge.order_item_id:
        order_item = OrderItem.query.get(charge.order_item_id)
        if order_item:
            order_item.sale_unit_price = float(new_price)
    
    db.session.commit()

    return jsonify(charge.to_dict())


@accounting_bp.patch("/charges/<int:charge_id>/quantity")
def update_charge_quantity(charge_id):
    """Actualizar la cantidad de un cargo"""
    from ..models.charge import Charge
    from ..models.order_item import OrderItem
    from ..db import db

    charge = Charge.query.get_or_404(charge_id)
    data = request.get_json() or {}
    new_qty = data.get('charged_qty')

    if new_qty is None:
        return jsonify({"error": "charged_qty requerido"}), 400

    charge.charged_qty = float(new_qty)
    charge.total = float(charge.charged_qty or 0.0) * float(charge.unit_price or 0.0)
    
    # TAMBIÉN actualizar el OrderItem relacionado para que el resumen de pedido refleje la nueva cantidad
    if charge.order_item_id:
        order_item = OrderItem.query.get(charge.order_item_id)
        if order_item:
            order_item.charged_qty = float(new_qty)
    
    db.session.commit()

    return jsonify(charge.to_dict())


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
                o = orders.setdefault(ch.order_id or 0, {
                    "order_id": ch.order_id, 
                    "billed": 0.0, 
                    "paid": 0.0,
                    "products": []
                })
                # Usar charged_qty para el cálculo por pedido también
                qty_to_charge = ch.charged_qty if ch.charged_qty is not None else float(ch.qty or 0.0)
                o["billed"] += max(0.0, (qty_to_charge * float(ch.unit_price or 0.0)) - (ch.discount_amount or 0.0))
                
                # Agregar detalle del producto
                from ..models.product import Product
                product = Product.query.get(ch.product_id) if ch.product_id else None
                o["products"].append({
                    "charge_id": ch.id,
                    "product_id": ch.product_id,
                    "product_name": product.name if product else "Desconocido",
                    "qty": ch.qty,
                    "charged_qty": ch.charged_qty,
                    "unit": ch.unit,
                    "unit_price": ch.unit_price,
                    "total": max(0.0, (qty_to_charge * float(ch.unit_price or 0.0)) - (ch.discount_amount or 0.0))
                })
            
            apps = PaymentApplication.query.filter(PaymentApplication.charge_id.in_(charge_ids)).all() if charge_ids else []
            paid_by_charge = {}
            for a in apps:
                paid_by_charge[a.charge_id] = (paid_by_charge.get(a.charge_id) or 0.0) + (a.amount or 0.0)
            for ch in charges:
                orders[ch.order_id or 0]["paid"] += paid_by_charge.get(ch.id, 0.0)
            row["orders"] = list(orders.values())
        
        result.append(row)
    return jsonify(result)



