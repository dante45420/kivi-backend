from flask import Blueprint, jsonify, request
from datetime import date
from typing import Optional

from ..db import db
from ..models.customer import Customer
from ..models.product import Product
from ..models.order import Order
from ..models.catalog_price import CatalogPrice
from ..models.order_item import OrderItem
from ..models.purchase import Purchase
from ..models.charge import Charge
from ..models.variant import VariantPriceTier
from ..services.order_parser import parse_orders_text
from ..utils.text_match import similarity_score, normalize_text
from .auth import require_token


orders_bp = Blueprint("orders", __name__)


def _score_name(query: str, name: str) -> int:
    return similarity_score(query, name)


def _get_draft(create: bool = False) -> Optional[Order]:
    draft = Order.query.filter_by(status="draft").order_by(Order.created_at.desc()).first()
    if draft or not create:
        return draft
    draft = Order(status="draft")
    db.session.add(draft); db.session.flush()
    draft.title = f"Pedido Nro {draft.id} - {date.today().isoformat()}"
    db.session.commit()
    return draft


@orders_bp.get("/orders")
def list_orders():
    items = Order.query.order_by(Order.created_at.desc()).limit(100).all()
    return jsonify([o.to_dict() for o in items])


@orders_bp.get("/orders/<int:order_id>")
def order_detail(order_id: int):
    order = Order.query.get_or_404(order_id)
    items = OrderItem.query.filter_by(order_id=order_id).all()
    customer_ids = {it.customer_id for it in items}
    product_ids = {it.product_id for it in items}
    customers = {c.id: c.name for c in Customer.query.filter(Customer.id.in_(customer_ids)).all()} if customer_ids else {}
    products = {p.id: p.name for p in Product.query.filter(Product.id.in_(product_ids)).all()} if product_ids else {}

    # Detalles de items
    items_detailed = []
    for it in items:
        items_detailed.append({
            **it.to_dict(),
            "customer_name": customers.get(it.customer_id),
            "product_name": products.get(it.product_id),
            "has_note": bool((it.notes or "").strip()),
        })

    by_product = {}
    by_customer = {}
    grouped_by_product = {}

    for it in items_detailed:
        by_product[it["product_id"]] = by_product.get(it["product_id"], 0.0) + it["qty"]
        by_customer[it["customer_id"]] = by_customer.get(it["customer_id"], 0.0) + it["qty"]
        gp = grouped_by_product.setdefault(it["product_id"], {
            "product_id": it["product_id"],
            "product_name": it["product_name"],
            "customers": [],
            "has_notes": False,
            "totals": {"kg": 0.0, "unit": 0.0, "g": 0.0},
        })
        gp["customers"].append({
            "customer_id": it["customer_id"],
            "customer_name": it["customer_name"],
            "qty": it["qty"],
            "unit": it["unit"],
            "has_note": it["has_note"],
        })
        if it["unit"] in gp["totals"]:
            gp["totals"][it["unit"]] += it["qty"]
        else:
            gp["totals"][it["unit"]] = gp["totals"].get(it["unit"], 0.0) + it["qty"]
        if it["has_note"]:
            gp["has_notes"] = True

    grouped_by_product_list = []
    for pid, info in grouped_by_product.items():
        customers_str = ", ".join(
            f"{c['customer_name']}({c['qty']} {c['unit']}{', nota' if c['has_note'] else ''})" for c in info["customers"]
        )
        grouped_by_product_list.append({
            "product_id": pid,
            "product_name": info["product_name"],
            "customers": info["customers"],
            "customers_str": customers_str,
            "has_notes": info["has_notes"],
            "totals": info["totals"],
        })

    # compras acumuladas por producto y unidad
    purchases = Purchase.query.filter_by(order_id=order_id).all()
    purchased_by_product = {}
    for p in purchases:
        d = purchased_by_product.setdefault(p.product_id, {"kg": 0.0, "unit": 0.0, "g": 0.0})
        if p.qty_kg:
            d["kg"] += p.qty_kg
        if getattr(p, "qty_unit", None):
            d["unit"] += p.qty_unit or 0.0

    return jsonify({
        "order": order.to_dict(),
        "items": [i for i in items_detailed],
        "by_product": by_product,
        "by_customer": by_customer,
        "group_by_product": grouped_by_product_list,
        "purchased_by_product": purchased_by_product,
        "customers": customers,
        "products": products,
    })


@orders_bp.get("/orders/draft")
def get_draft():
    d = _get_draft(create=True)
    return jsonify(d.to_dict())


@orders_bp.get("/orders/draft/detail")
def draft_detail():
    d = _get_draft(create=True)
    return order_detail(d.id)


@orders_bp.post("/orders/parse")
def parse_orders():
    data = request.get_json(silent=True) or {}; text = data.get("text") or ""
    parsed = parse_orders_text(text)
    all_products = Product.query.all()
    canon = {normalize_text(p.name): p for p in all_products}
    def annotate(it):
        name = (it.get("product") or "").strip()
        if not name:
            return {**it, "match_status": "none"}
        nname = normalize_text(name)
        if nname in canon:
            p = canon[nname]
            return {**it, "match_status": "exact", "product_id": p.id}
        ranked = sorted((( _score_name(name, p.name), p ) for p in all_products), key=lambda x: -x[0])
        suggestions = [{"id": p.id, "name": p.name, "score": s} for s, p in ranked if s >= 70][:5]
        if suggestions:
            return {**it, "match_status": "similar", "suggestions": suggestions}
        return {**it, "match_status": "none"}
    items = [annotate(it) for it in parsed]
    return jsonify({"items": items})


@orders_bp.post("/orders/validate")
def validate_orders():
    data = request.get_json(silent=True) or {}; items = data.get("items") or []
    result = {"resolved": [], "ambiguous": []}
    all_products = Product.query.all()
    for it in items:
        name = (it.get("product") or "").strip()
        if not name: continue
        exact = Product.query.filter(Product.name.ilike(name)).first()
        if exact:
            result["resolved"].append({**it, "product_id": exact.id, "matched_name": exact.name}); continue
        ranked = sorted((( _score_name(name, p.name), p ) for p in all_products), key=lambda x: -x[0])
        suggestions = [{"id": p.id, "name": p.name, "score": s} for s, p in ranked if s >= 70][:5]
        result["ambiguous"].append({**it, "suggestions": suggestions})
    return jsonify(result)


def _create_product_with_kivi(product_name: str, sale_price: float, default_unit: str) -> Product:
    """Crea un producto con precio de catálogo y variante kivi automática"""
    product = Product(name=product_name, default_unit=default_unit)
    db.session.add(product)
    db.session.flush()
    
    # Agregar precio de catálogo
    db.session.add(CatalogPrice(
        product_id=product.id, 
        date=date.today(), 
        sale_price=sale_price, 
        unit=default_unit
    ))
    
    # Crear variante kivi automáticamente
    try:
        from ..models.variant import ProductVariant, VariantPriceTier
        db.session.flush()
        kivi_variant = ProductVariant(product_id=product.id, label='kivi', active=True)
        db.session.add(kivi_variant)
        db.session.flush()
        kivi_tier = VariantPriceTier(
            product_id=product.id,
            variant_id=kivi_variant.id,
            min_qty=1.0,
            unit=default_unit,
            sale_price=sale_price
        )
        db.session.add(kivi_tier)
    except Exception:
        pass
    
    return product


def _add_items(order: Order, items: list[dict]) -> None:
    for it in items:
        customer_name = (it.get("customer") or "").strip()
        product_id = it.get("product_id"); product_name = (it.get("product") or "").strip(); variant_id = it.get("variant_id")
        create_if_missing = bool(it.get("create_if_missing"))
        variant_id = it.get("variant_id")
        sale_unit_price = it.get("sale_unit_price")
        if not customer_name: continue
        customer = Customer.query.filter_by(name=customer_name).first()
        if not customer:
            customer = Customer(name=customer_name); db.session.add(customer); db.session.flush()
        product = Product.query.get(product_id) if product_id else Product.query.filter(Product.name.ilike(product_name)).first()
        if not product and create_if_missing and product_name:
            # Requiere precio de venta inicial
            try:
                sale_price = float(it.get("sale_price")) if it.get("sale_price") is not None else None
            except (TypeError, ValueError):
                sale_price = None
            if sale_price is None or sale_price <= 0:
                # no se puede crear sin precio de venta
                continue
            default_unit = (it.get("default_unit") or it.get("unit") or "kg")
            product = _create_product_with_kivi(product_name, sale_price, default_unit)
        if not product: continue
        db.session.add(OrderItem(order_id=order.id, customer_id=customer.id, product_id=product.id, qty=float(it.get("qty") or 0), unit=(it.get("unit") or "kg"), notes=it.get("notes"), variant_id=(int(variant_id) if variant_id else None), sale_unit_price=(float(sale_unit_price) if sale_unit_price is not None else None)))


@orders_bp.post("/orders/draft/items")
@require_token
def add_items_to_current_draft():
    d = _get_draft(create=True)
    data = request.get_json(silent=True) or {}; items = data.get("items") or []
    inserted = 0
    skipped = []
    for idx, it in enumerate(items):
        line_idx = it.get("line_index", idx)
        customer_name = (it.get("customer") or "").strip()
        if not customer_name:
            skipped.append({"index": line_idx, "reason": "missing_customer"})
            continue
        customer = Customer.query.filter_by(name=customer_name).first()
        if not customer:
            customer = Customer(name=customer_name); db.session.add(customer); db.session.flush()

        product_id = it.get("product_id"); product_name = (it.get("product") or "").strip(); variant_id = it.get("variant_id"); sale_unit_price = it.get("sale_unit_price")
        create_if_missing = bool(it.get("create_if_missing"))
        product = Product.query.get(product_id) if product_id else Product.query.filter(Product.name.ilike(product_name)).first()
        if not product and not create_if_missing:
            skipped.append({"index": line_idx, "reason": "unresolved_product", "product": product_name})
            continue
        if not product and create_if_missing and product_name:
            # Requiere precio de venta inicial cuando se crea desde pedidos
            try:
                sale_price = float(it.get("sale_price")) if it.get("sale_price") is not None else None
            except (TypeError, ValueError):
                sale_price = None
            if sale_price is None or sale_price <= 0:
                skipped.append({"index": line_idx, "reason": "missing_sale_price", "product": product_name})
                continue
            default_unit = (it.get("default_unit") or it.get("unit") or "kg")
            product = _create_product_with_kivi(product_name, sale_price, default_unit)

        if not product:
            skipped.append({"index": line_idx, "reason": "empty_product_name"})
            continue

        # charged_unit por defecto desde el producto reconocido/creado
        charged_unit = (it.get("charged_unit") or getattr(product, 'default_unit', None) or it.get("unit") or "kg")
        charged_qty = None
        try:
            if charged_unit and (it.get("unit") or "kg") != charged_unit:
                # si r viene desde frontend, úsalo; de lo contrario, deja None
                charged_qty = float(it.get("charged_qty")) if it.get("charged_qty") is not None else None
        except Exception:
            charged_qty = None
        db.session.add(OrderItem(order_id=d.id, customer_id=customer.id, product_id=product.id, qty=float(it.get("qty") or 0), unit=(it.get("unit") or "kg"), charged_unit=charged_unit, charged_qty=charged_qty, notes=it.get("notes"), variant_id=(int(variant_id) if variant_id else None), sale_unit_price=(float(sale_unit_price) if sale_unit_price is not None else None)))
        inserted += 1

    db.session.commit()
    return jsonify({"ok": True, "order": d.to_dict(), "inserted": inserted, "skipped": skipped})


@orders_bp.post("/orders/draft/confirm")
@require_token
def confirm_current_draft():
    d = _get_draft(create=True)
    # Generar cargos si aún no existen para este pedido
    existing = Charge.query.filter(Charge.order_id == d.id).first()
    if not existing:
        items = OrderItem.query.filter_by(order_id=d.id).all()
        for it in items:
            # Resolver precio: si viene fijado, usarlo; si no, determinar por variante en charged_unit
            unit_price = float(it.sale_unit_price) if (it.sale_unit_price is not None) else 0.0
            if unit_price <= 0:
                variant_id = it.variant_id
                q = VariantPriceTier.query.filter(VariantPriceTier.product_id == it.product_id, VariantPriceTier.unit == (it.charged_unit or it.unit or "kg"))
                if variant_id is not None:
                    q = q.filter((VariantPriceTier.variant_id == variant_id) | (VariantPriceTier.variant_id.is_(None)))
                tiers = q.order_by(VariantPriceTier.min_qty.desc()).all()
                for t in tiers:
                    if float(it.qty or 0) >= float(t.min_qty or 0):
                        unit_price = float(t.sale_price or 0.0)
                        break
            if unit_price <= 0:
                c = (
                    CatalogPrice.query.filter(CatalogPrice.product_id == it.product_id)
                    .order_by(CatalogPrice.date.desc())
                    .first()
                )
                unit_price = float(c.sale_price) if c else 0.0
            # Cantidad a cobrar: usar charged_qty si existe (si ya se compró), si no usar qty como placeholder
            q_charge = float(it.charged_qty) if (getattr(it, 'charged_qty', None) is not None) else float(it.qty or 0)
            total = q_charge * float(unit_price or 0)
            db.session.add(Charge(
                customer_id=it.customer_id, 
                order_id=d.id,
                original_order_id=d.id,  # pedido original
                order_item_id=it.id, 
                product_id=it.product_id, 
                qty=float(it.qty or 0),  # cantidad pedida original
                charged_qty=float(it.charged_qty) if (it.charged_qty is not None) else None,  # cantidad a cobrar (puede ser None inicialmente)
                unit=(it.charged_unit or it.unit or "kg"), 
                unit_price=unit_price or 0.0, 
                discount_amount=0.0, 
                discount_reason=None, 
                status="pending", 
                total=total
            ))
        db.session.flush()
    d.status = "emitido"
    db.session.commit()
    return jsonify(d.to_dict())


@orders_bp.post("/orders")
@require_token
def create_order():
    data = request.get_json(silent=True) or {}; items = data.get("items") or []
    notes = data.get("notes")
    order = Order(notes=notes, status="emitido"); db.session.add(order); db.session.flush()
    _add_items(order, items); db.session.commit()
    order.title = f"Pedido Nro {order.id} - {date.today().isoformat()}"; db.session.commit()
    return jsonify(order.to_dict()), 201


@orders_bp.post("/orders/<int:order_id>/items")
@require_token
def add_items_to_order(order_id: int):
    """Agregar items a un pedido existente (incluso si está emitido)"""
    order = Order.query.get_or_404(order_id)
    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    
    inserted = 0
    skipped = []
    
    for idx, it in enumerate(items):
        line_idx = it.get("line_index", idx)
        customer_name = (it.get("customer") or "").strip()
        
        if not customer_name:
            skipped.append({"index": line_idx, "reason": "missing_customer"})
            continue
            
        customer = Customer.query.filter_by(name=customer_name).first()
        if not customer:
            customer = Customer(name=customer_name)
            db.session.add(customer)
            db.session.flush()
        
        product_id = it.get("product_id")
        product_name = (it.get("product") or "").strip()
        variant_id = it.get("variant_id")
        sale_unit_price = it.get("sale_unit_price")
        create_if_missing = bool(it.get("create_if_missing"))
        
        product = Product.query.get(product_id) if product_id else Product.query.filter(Product.name.ilike(product_name)).first()
        
        if not product and not create_if_missing:
            skipped.append({"index": line_idx, "reason": "unresolved_product", "product": product_name})
            continue
            
        if not product and create_if_missing and product_name:
            try:
                sale_price = float(it.get("sale_price")) if it.get("sale_price") is not None else None
            except (TypeError, ValueError):
                sale_price = None
                
            if sale_price is None or sale_price <= 0:
                skipped.append({"index": line_idx, "reason": "missing_sale_price", "product": product_name})
                continue
                
            default_unit = (it.get("default_unit") or it.get("unit") or "kg")
            product = _create_product_with_kivi(product_name, sale_price, default_unit)
        
        if not product:
            skipped.append({"index": line_idx, "reason": "empty_product_name"})
            continue
        
        # Crear el OrderItem
        charged_unit = (it.get("charged_unit") or getattr(product, 'default_unit', None) or it.get("unit") or "kg")
        charged_qty = None
        try:
            if charged_unit and (it.get("unit") or "kg") != charged_unit:
                charged_qty = float(it.get("charged_qty")) if it.get("charged_qty") is not None else None
        except Exception:
            charged_qty = None
            
        order_item = OrderItem(
            order_id=order.id,
            customer_id=customer.id,
            product_id=product.id,
            qty=float(it.get("qty") or 0),
            unit=(it.get("unit") or "kg"),
            charged_unit=charged_unit,
            charged_qty=charged_qty,
            notes=it.get("notes"),
            variant_id=(int(variant_id) if variant_id else None),
            sale_unit_price=(float(sale_unit_price) if sale_unit_price is not None else None)
        )
        db.session.add(order_item)
        db.session.flush()
        
        # Si el pedido está emitido, crear el cargo automáticamente
        if order.status == "emitido":
            unit_price = float(sale_unit_price) if (sale_unit_price is not None) else 0.0
            
            if unit_price <= 0:
                variant_id = it.get("variant_id")
                q = VariantPriceTier.query.filter(
                    VariantPriceTier.product_id == product.id,
                    VariantPriceTier.unit == charged_unit
                )
                if variant_id is not None:
                    q = q.filter((VariantPriceTier.variant_id == variant_id) | (VariantPriceTier.variant_id.is_(None)))
                tiers = q.order_by(VariantPriceTier.min_qty.desc()).all()
                for t in tiers:
                    if float(it.get("qty") or 0) >= float(t.min_qty or 0):
                        unit_price = float(t.sale_price or 0.0)
                        break
            
            if unit_price <= 0:
                c = (
                    CatalogPrice.query.filter(CatalogPrice.product_id == product.id)
                    .order_by(CatalogPrice.date.desc())
                    .first()
                )
                unit_price = float(c.sale_price) if c else 0.0
            
            q_charge = float(charged_qty) if (charged_qty is not None) else float(it.get("qty") or 0)
            total = q_charge * float(unit_price or 0)
            
            db.session.add(Charge(
                customer_id=customer.id,
                order_id=order.id,
                original_order_id=order.id,
                order_item_id=order_item.id,
                product_id=product.id,
                qty=float(it.get("qty") or 0),
                charged_qty=charged_qty,
                unit=charged_unit,
                unit_price=unit_price or 0.0,
                discount_amount=0.0,
                discount_reason=None,
                status="pending",
                total=total
            ))
        
        inserted += 1
    
    db.session.commit()
    return jsonify({"ok": True, "order": order.to_dict(), "inserted": inserted, "skipped": skipped})


@orders_bp.delete("/orders/<int:order_id>/items/<int:item_id>")
@require_token
def delete_order_item(order_id: int, item_id: int):
    """Eliminar un item de un pedido y sus charges asociados"""
    order = Order.query.get_or_404(order_id)
    item = OrderItem.query.filter_by(id=item_id, order_id=order_id).first_or_404()
    
    try:
        # Eliminar charges asociados
        charges = Charge.query.filter_by(order_item_id=item.id).all()
        for charge in charges:
            db.session.delete(charge)
        
        # Eliminar el item
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({"message": "Item eliminado exitosamente"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
