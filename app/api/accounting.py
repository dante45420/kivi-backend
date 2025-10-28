from flask import Blueprint, jsonify, request

from ..db import db
from ..models.order import Order
from ..models.customer import Customer
from ..models.charge import Charge
from ..models.payment import PaymentApplication
from ..models.order_item import OrderItem
from ..models.purchase import Purchase
from ..models.variant import VariantPriceTier
from ..models.catalog_price import CatalogPrice
from .auth import require_token


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
    
    Los vendedores solo ven sus propias órdenes.
    """
    # Retrocompatibilidad: funciona con o sin autenticación
    user = getattr(request, 'current_user', None)
    include_details = request.args.get('include_details') == '1'
    
    query = Order.query
    
    # Si es vendedor, filtrar solo sus órdenes
    if user and user.role == 'vendor':
        query = query.filter(Order.vendor_id == user.id)
    
    orders = query.order_by(Order.created_at.desc()).limit(200).all()
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
        
        # ===== 6. COMISIONES DE VENDEDORES =====
        vendor_commission_amount = 0.0
        vendor_commission_pct = 0.0
        kivi_amount = 0.0
        vendor_info = None
        
        # Si el pedido tiene un vendedor asignado, calcular su comisión
        if o.vendor_id:
            from ..models.user import User
            vendor = User.query.get(o.vendor_id)
            if vendor:
                profit_amount = max(0.0, billed_total - total_cost)
                vendor_commission_pct = vendor.commission_rate * 100  # Convertir a porcentaje para display
                vendor_commission_amount = profit_amount * vendor.commission_rate
                kivi_amount = profit_amount - vendor_commission_amount
                vendor_info = {
                    "vendor_id": vendor.id,
                    "vendor_name": vendor.name,
                    "commission_rate": vendor.commission_rate
                }
        else:
            # Si no hay vendedor, toda la utilidad es para Kivi
            profit_amount = max(0.0, billed_total - total_cost)
            kivi_amount = profit_amount
        
        # ===== 7. RESULTADO =====
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
                # Comisiones de vendedor
                "vendor_commission_amount": vendor_commission_amount,
                "vendor_commission_pct": vendor_commission_pct,
                "kivi_amount": kivi_amount,
                "vendor_info": vendor_info,
                "bought_money": 0.0,  # No usado en frontend
                "missing_money": 0.0,  # No usado en frontend
            "bought_tags": bought_tags,
            "missing_tags": missing_tags,
            "billed_by_customer": billed_by_customer,
            }
            
            if include_details:
                row["customers"] = customers_detail
                # Incluir detalles de compras con información de productos
                from ..models.product import Product
                purchases_detail = []
                for purchase in purchases:
                    product = Product.query.get(purchase.product_id)
                    purchases_detail.append({
                        **purchase.to_dict(),
                        "product_name": product.name if product else f"Producto #{purchase.product_id}"
                    })
                row["purchases"] = purchases_detail
            
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


@accounting_bp.get("/accounting/excess")
def calculate_excess():
    """
    Calcular excedentes simples: diferencia entre lo comprado y lo pedido
    (en la unidad de cobro, con conversiones aplicadas)
    """
    orders = Order.query.order_by(Order.created_at.desc()).limit(50).all()
    result = []
    
    for o in orders:
        # Obtener items y compras del pedido
        items = OrderItem.query.filter_by(order_id=o.id).all()
        purchases = Purchase.query.filter_by(order_id=o.id).all()
        
        if not purchases:
            continue
        
        # Agrupar lo pedido por producto en la unidad de cobro
        needed_by_product = {}
        for item in items:
            pid = item.product_id
            charged_unit = item.charged_unit or item.unit or "kg"
            charged_qty = item.charged_qty if item.charged_qty is not None else float(item.qty or 0.0)
            
            if pid not in needed_by_product:
                needed_by_product[pid] = {"unit": charged_unit, "qty": 0.0}
            needed_by_product[pid]["qty"] += charged_qty
        
        # Agrupar lo comprado por producto en la unidad de cobro
        purchased_by_product = {}
        for purchase in purchases:
            pid = purchase.product_id
            charged_unit = purchase.charged_unit or "kg"
            
            if pid not in purchased_by_product:
                purchased_by_product[pid] = {"unit": charged_unit, "qty": 0.0}
            
            # Sumar la cantidad comprada en la unidad de cobro
            if charged_unit == "kg":
                purchased_by_product[pid]["qty"] += float(purchase.qty_kg or 0.0)
                if purchase.eq_qty_kg:
                    purchased_by_product[pid]["qty"] += float(purchase.eq_qty_kg or 0.0)
            else:  # unit
                purchased_by_product[pid]["qty"] += float(purchase.qty_unit or 0.0)
                if purchase.eq_qty_unit:
                    purchased_by_product[pid]["qty"] += float(purchase.eq_qty_unit or 0.0)
        
        # Calcular excedentes: comprado - pedido (simple)
        excesses = []
        for pid, purchased in purchased_by_product.items():
            needed = needed_by_product.get(pid, {"unit": purchased["unit"], "qty": 0.0})
            
            # Excedente simple = comprado - pedido
            excess_qty = purchased["qty"] - needed["qty"]
            
            if excess_qty > 0.01:  # Solo si hay excedente
                from ..models.product import Product
                product = Product.query.get(pid)
                excesses.append({
                    "order_id": o.id,
                    "product_id": pid,
                    "product_name": product.name if product else f"Producto #{pid}",
                    "excess_qty": round(excess_qty, 2),
                    "unit": purchased["unit"],
                    "needed_qty": round(needed["qty"], 2),
                    "purchased_qty": round(purchased["qty"], 2),
                    "reassigned_qty": 0.0  # Sin reasignaciones en el cálculo
                })
        
        if excesses:
            result.append({
                "order": o.to_dict(),
                "excesses": excesses
            })
    
    # Obtener compras SIN order_id (compras de excedente que no corresponden a un pedido)
    orphan_purchases = Purchase.query.filter(Purchase.order_id.is_(None)).all()
    
    # Agrupar por producto
    if orphan_purchases:
        orphan_by_product = {}
        for purchase in orphan_purchases:
            pid = purchase.product_id
            charged_unit = purchase.charged_unit or "kg"
            
            if pid not in orphan_by_product:
                orphan_by_product[pid] = {"unit": charged_unit, "qty": 0.0}
            
            if charged_unit == "kg":
                orphan_by_product[pid]["qty"] += float(purchase.qty_kg or 0.0)
                if purchase.eq_qty_kg:
                    orphan_by_product[pid]["qty"] += float(purchase.eq_qty_kg or 0.0)
            else:  # unit
                orphan_by_product[pid]["qty"] += float(purchase.qty_unit or 0.0)
                if purchase.eq_qty_unit:
                    orphan_by_product[pid]["qty"] += float(purchase.eq_qty_unit or 0.0)
        
        # Crear una entrada especial para excedentes sin pedido
        orphan_excesses = []
        for pid, purchased in orphan_by_product.items():
            from ..models.product import Product
            product = Product.query.get(pid)
            orphan_excesses.append({
                "order_id": None,
                "product_id": pid,
                "product_name": product.name if product else f"Producto #{pid}",
                "excess_qty": round(purchased["qty"], 2),
                "unit": purchased["unit"],
                "needed_qty": 0.0,
                "purchased_qty": round(purchased["qty"], 2),
                "reassigned_qty": 0.0
            })
        
        if orphan_excesses:
            result.append({
                "order": {"id": None, "title": "Excedentes sin pedido", "status": "excedentes"},
                "excesses": orphan_excesses
            })
    
    return jsonify(result)


@accounting_bp.get("/accounting/excess/debug")
def debug_excess():
    """
    Debug del cálculo de excedentes para ver exactamente qué está pasando
    """
    order_id = request.args.get('order_id')
    if not order_id:
        return jsonify({"error": "order_id requerido"}), 400
    
    order = Order.query.get(int(order_id))
    if not order:
        return jsonify({"error": "Pedido no encontrado"}), 404
    
    # Obtener items y compras del pedido
    items = OrderItem.query.filter_by(order_id=order.id).all()
    purchases = Purchase.query.filter_by(order_id=order.id).all()
    
    # Debug de items
    items_debug = []
    for item in items:
        items_debug.append({
            "id": item.id,
            "product_id": item.product_id,
            "qty": item.qty,
            "unit": item.unit,
            "charged_qty": item.charged_qty,
            "charged_unit": item.charged_unit,
            "customer_id": item.customer_id
        })
    
    # Debug de compras
    purchases_debug = []
    for purchase in purchases:
        purchases_debug.append({
            "id": purchase.id,
            "product_id": purchase.product_id,
            "qty_kg": purchase.qty_kg,
            "qty_unit": purchase.qty_unit,
            "eq_qty_kg": purchase.eq_qty_kg,
            "eq_qty_unit": purchase.eq_qty_unit,
            "charged_unit": purchase.charged_unit
        })
    
    # Agrupar lo pedido
    needed_by_product = {}
    for item in items:
        pid = item.product_id
        charged_unit = item.charged_unit or item.unit or "kg"
        charged_qty = item.charged_qty if item.charged_qty is not None else float(item.qty or 0.0)
        
        if pid not in needed_by_product:
            needed_by_product[pid] = {"unit": charged_unit, "qty": 0.0}
        needed_by_product[pid]["qty"] += charged_qty
    
    # Agrupar lo comprado
    purchased_by_product = {}
    for purchase in purchases:
        pid = purchase.product_id
        charged_unit = purchase.charged_unit or "kg"
        
        if pid not in purchased_by_product:
            purchased_by_product[pid] = {"unit": charged_unit, "qty": 0.0}
        
        if charged_unit == "kg":
            purchased_by_product[pid]["qty"] += float(purchase.qty_kg or 0.0)
            if purchase.eq_qty_kg:
                purchased_by_product[pid]["qty"] += float(purchase.eq_qty_kg or 0.0)
        else:  # unit
            purchased_by_product[pid]["qty"] += float(purchase.qty_unit or 0.0)
            if purchase.eq_qty_unit:
                purchased_by_product[pid]["qty"] += float(purchase.eq_qty_unit or 0.0)
    
    return jsonify({
        "order": order.to_dict(),
        "items": items_debug,
        "purchases": purchases_debug,
        "needed_by_product": needed_by_product,
        "purchased_by_product": purchased_by_product
    })


@accounting_bp.get("/accounting/debug/orders")
def debug_orders():
    """
    Debug simple para ver todos los pedidos y sus items
    """
    orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    result = []
    
    for order in orders:
        items = OrderItem.query.filter_by(order_id=order.id).all()
        purchases = Purchase.query.filter_by(order_id=order.id).all()
        
        order_debug = {
            "order_id": order.id,
            "order_title": order.title,
            "order_status": order.status,
            "items_count": len(items),
            "purchases_count": len(purchases),
            "items": [],
            "purchases": []
        }
        
        for item in items:
            order_debug["items"].append({
                "id": item.id,
                "product_id": item.product_id,
                "qty": item.qty,
                "unit": item.unit,
                "charged_qty": item.charged_qty,
                "charged_unit": item.charged_unit
            })
        
        for purchase in purchases:
            order_debug["purchases"].append({
                "id": purchase.id,
                "product_id": purchase.product_id,
                "qty_kg": purchase.qty_kg,
                "qty_unit": purchase.qty_unit,
                "charged_unit": purchase.charged_unit
            })
        
        result.append(order_debug)
    
    return jsonify(result)


@accounting_bp.get("/accounting/excess/simple")
def calculate_excess_simple():
    """
    Calcular excedentes simples: solo diferencia entre lo comprado y lo pedido
    (sin considerar reasignaciones)
    """
    orders = Order.query.order_by(Order.created_at.desc()).limit(50).all()
    result = []
    
    for o in orders:
        # Obtener items y compras del pedido
        items = OrderItem.query.filter_by(order_id=o.id).all()
        purchases = Purchase.query.filter_by(order_id=o.id).all()
        
        if not purchases:
            continue
        
        # Agrupar lo pedido por producto
        needed_by_product = {}
        for item in items:
            pid = item.product_id
            charged_unit = item.charged_unit or item.unit or "kg"
            charged_qty = item.charged_qty if item.charged_qty is not None else float(item.qty or 0.0)
            
            if pid not in needed_by_product:
                needed_by_product[pid] = {"unit": charged_unit, "qty": 0.0}
            needed_by_product[pid]["qty"] += charged_qty
        
        # Agrupar lo comprado por producto
        purchased_by_product = {}
        for purchase in purchases:
            pid = purchase.product_id
            charged_unit = purchase.charged_unit or "kg"
            
            if pid not in purchased_by_product:
                purchased_by_product[pid] = {"unit": charged_unit, "qty": 0.0}
            
            if charged_unit == "kg":
                purchased_by_product[pid]["qty"] += float(purchase.qty_kg or 0.0)
                if purchase.eq_qty_kg:
                    purchased_by_product[pid]["qty"] += float(purchase.eq_qty_kg or 0.0)
            else:  # unit
                purchased_by_product[pid]["qty"] += float(purchase.qty_unit or 0.0)
                if purchase.eq_qty_unit:
                    purchased_by_product[pid]["qty"] += float(purchase.eq_qty_unit or 0.0)
        
        # Calcular excedentes: comprado - pedido (sin reasignaciones)
        excesses = []
        for pid, purchased in purchased_by_product.items():
            needed = needed_by_product.get(pid, {"unit": purchased["unit"], "qty": 0.0})
            
            # Excedente simple = comprado - pedido
            excess_qty = purchased["qty"] - needed["qty"]
            
            if excess_qty > 0.01:  # Solo si hay excedente
                from ..models.product import Product
                product = Product.query.get(pid)
                excesses.append({
                    "order_id": o.id,
                    "product_id": pid,
                    "product_name": product.name if product else f"Producto #{pid}",
                    "excess_qty": round(excess_qty, 2),
                    "unit": purchased["unit"],
                    "needed_qty": round(needed["qty"], 2),
                    "purchased_qty": round(purchased["qty"], 2),
                    "reassigned_qty": 0.0  # Sin reasignaciones
                })
        
        if excesses:
            result.append({
                "order": o.to_dict(),
                "excesses": excesses
            })
    
    return jsonify(result)


@accounting_bp.get("/accounting/excess/test")
def test_excess_calculation():
    """
    Test específico del cálculo de excedentes para el pedido 7
    """
    order_id = 7
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Pedido 7 no encontrado"}), 404
    
    # Obtener items y compras del pedido
    items = OrderItem.query.filter_by(order_id=order.id).all()
    purchases = Purchase.query.filter_by(order_id=order.id).all()
    
    # Agrupar lo pedido por producto
    needed_by_product = {}
    for item in items:
        pid = item.product_id
        charged_unit = item.charged_unit or item.unit or "kg"
        charged_qty = item.charged_qty if item.charged_qty is not None else float(item.qty or 0.0)
        
        if pid not in needed_by_product:
            needed_by_product[pid] = {"unit": charged_unit, "qty": 0.0}
        needed_by_product[pid]["qty"] += charged_qty
    
    # Agrupar lo comprado por producto
    purchased_by_product = {}
    for purchase in purchases:
        pid = purchase.product_id
        charged_unit = purchase.charged_unit or "kg"
        
        if pid not in purchased_by_product:
            purchased_by_product[pid] = {"unit": charged_unit, "qty": 0.0}
        
        if charged_unit == "kg":
            purchased_by_product[pid]["qty"] += float(purchase.qty_kg or 0.0)
            if purchase.eq_qty_kg:
                purchased_by_product[pid]["qty"] += float(purchase.eq_qty_kg or 0.0)
        else:  # unit
            purchased_by_product[pid]["qty"] += float(purchase.qty_unit or 0.0)
            if purchase.eq_qty_unit:
                purchased_by_product[pid]["qty"] += float(purchase.eq_qty_unit or 0.0)
    
    # Calcular excedentes
    excesses = []
    for pid, purchased in purchased_by_product.items():
        needed = needed_by_product.get(pid, {"unit": purchased["unit"], "qty": 0.0})
        excess_qty = purchased["qty"] - needed["qty"]
        
        from ..models.product import Product
        product = Product.query.get(pid)
        
        excesses.append({
            "product_id": pid,
            "product_name": product.name if product else f"Producto #{pid}",
            "needed_qty": round(needed["qty"], 2),
            "purchased_qty": round(purchased["qty"], 2),
            "excess_qty": round(excess_qty, 2),
            "unit": purchased["unit"],
            "has_excess": excess_qty > 0.01
        })
    
    return jsonify({
        "order_id": order_id,
        "order_title": order.title,
        "needed_by_product": needed_by_product,
        "purchased_by_product": purchased_by_product,
        "excesses": excesses
    })


@accounting_bp.get("/accounting/vendors/commissions")
@require_token
def vendors_commissions_summary():
    """
    Resumen de comisiones a pagar a vendedores.
    Solo accesible para admin.
    
    Retorna un resumen por vendedor con:
    - Total facturado
    - Total costos
    - Total utilidad
    - Comisión del vendedor
    - Cantidad para Kivi
    """
    user = getattr(request, 'current_user', None)
    
    # Solo admin puede ver este reporte
    if not user or user.role != 'admin':
        return jsonify({"error": "forbidden", "message": "Solo admins pueden ver este reporte"}), 403
    
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    
    from ..models.user import User
    from datetime import datetime
    
    # Obtener todos los vendedores
    vendors = User.query.filter_by(role='vendor', active=True).all()
    
    result = []
    
    for vendor in vendors:
        # Obtener órdenes del vendedor
        query = Order.query.filter(Order.vendor_id == vendor.id, Order.status == 'emitido')
        
        # Aplicar filtros de fecha si existen
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(Order.created_at >= date_from_obj)
            except:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                query = query.filter(Order.created_at <= date_to_obj)
            except:
                pass
        
        orders = query.all()
        
        if not orders:
            continue
        
        # Calcular totales para este vendedor
        total_billed = 0.0
        total_cost = 0.0
        
        for order in orders:
            # Facturado
            charges = Charge.query.filter(
                Charge.order_id == order.id,
                Charge.status != 'cancelled'
            ).all()
            
            for charge in charges:
                qty = charge.charged_qty if charge.charged_qty is not None else (charge.qty or 0)
                total_billed += qty * (charge.unit_price or 0)
            
            # Costos
            purchases = Purchase.query.filter_by(order_id=order.id).all()
            for purchase in purchases:
                if purchase.price_total:
                    total_cost += purchase.price_total
        
        # Calcular utilidad y comisiones
        profit = max(0.0, total_billed - total_cost)
        vendor_commission = profit * vendor.commission_rate
        kivi_amount = profit - vendor_commission
        
        result.append({
            "vendor_id": vendor.id,
            "vendor_name": vendor.name,
            "vendor_email": vendor.email,
            "commission_rate": vendor.commission_rate,
            "num_orders": len(orders),
            "total_billed": round(total_billed, 2),
            "total_cost": round(total_cost, 2),
            "total_profit": round(profit, 2),
            "vendor_commission": round(vendor_commission, 2),
            "kivi_amount": round(kivi_amount, 2)
        })
    
    # Ordenar por comisión descendente
    result.sort(key=lambda x: x['vendor_commission'], reverse=True)
    
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



