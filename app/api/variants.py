from flask import Blueprint, jsonify, request

from ..db import db
from ..models.variant import ProductVariant, VariantPriceTier
from .auth import require_token


variants_bp = Blueprint("variants", __name__)


@variants_bp.get("/variants")
def list_variants():
    product_id = request.args.get("product_id", type=int)
    q = ProductVariant.query
    if product_id:
        q = q.filter(ProductVariant.product_id == product_id)
    rows = q.order_by(ProductVariant.label.asc()).all()
    return jsonify([r.to_dict() for r in rows])


@variants_bp.post("/variants")
@require_token
def create_variant():
    data = request.get_json(silent=True) or {}
    v = ProductVariant(product_id=int(data.get("product_id")), label=(data.get("label") or "").strip(), active=bool(data.get("active") if data.get("active") is not None else True))
    db.session.add(v)
    db.session.commit()
    return jsonify(v.to_dict()), 201


@variants_bp.put("/variants/<int:variant_id>")
@require_token
def update_variant(variant_id: int):
    data = request.get_json(silent=True) or {}
    v = ProductVariant.query.get_or_404(variant_id)
    if "label" in data:
        v.label = (data.get("label") or v.label)
    if data.get("active") is not None:
        v.active = bool(data.get("active"))
    db.session.commit()
    return jsonify(v.to_dict())


@variants_bp.get("/variants/tiers")
def list_tiers():
    product_id = request.args.get("product_id", type=int)
    variant_id = request.args.get("variant_id", type=int)
    q = VariantPriceTier.query
    if product_id:
        q = q.filter(VariantPriceTier.product_id == product_id)
    if variant_id:
        q = q.filter(VariantPriceTier.variant_id == variant_id)
    rows = q.order_by(VariantPriceTier.min_qty.asc()).all()
    return jsonify([r.to_dict() for r in rows])


@variants_bp.post("/variants/tiers")
@require_token
def create_tier():
    data = request.get_json(silent=True) or {}
    t = VariantPriceTier(product_id=int(data.get("product_id")), variant_id=(int(data.get("variant_id")) if data.get("variant_id") else None), min_qty=float(data.get("min_qty") or 1.0), unit=(data.get("unit") or "kg"), sale_price=float(data.get("sale_price") or 0))
    db.session.add(t)
    db.session.commit()
    return jsonify(t.to_dict()), 201


@variants_bp.put("/variants/tiers/<int:tier_id>")
@require_token
def update_tier(tier_id: int):
    data = request.get_json(silent=True) or {}
    t = VariantPriceTier.query.get_or_404(tier_id)
    
    if "min_qty" in data:
        t.min_qty = float(data.get("min_qty") or 1.0)
    if "sale_price" in data:
        t.sale_price = float(data.get("sale_price") or 0)
    if "unit" in data:
        t.unit = data.get("unit") or "kg"
    
    db.session.commit()
    return jsonify(t.to_dict())


@variants_bp.delete("/variants/<int:variant_id>")
@require_token
def delete_variant(variant_id):
    """Eliminar una variante de producto"""
    from ..models.order_item import OrderItem
    
    variant = ProductVariant.query.get_or_404(variant_id)
    
    try:
        # Verificar si la variante está siendo usada en order_items
        order_items_using_variant = OrderItem.query.filter_by(variant_id=variant_id).count()
        
        if order_items_using_variant > 0:
            return jsonify({
                "error": f"No se puede eliminar esta variante porque está siendo usada en {order_items_using_variant} pedido(s). Primero debes actualizar o eliminar esos pedidos."
            }), 400
        
        # Eliminar primero los price tiers asociados
        VariantPriceTier.query.filter_by(variant_id=variant_id).delete()
        
        # Eliminar la variante
        db.session.delete(variant)
        db.session.commit()
        
        return jsonify({"message": "Variante eliminada exitosamente"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@variants_bp.delete("/variants/bulk/kivi")
@require_token
def delete_kivi_variants():
    """Eliminar todas las variantes llamadas 'kivi' o similares"""
    from ..models.order_item import OrderItem
    
    try:
        # Buscar variantes con el nombre kivi (case insensitive)
        kivi_variants = ProductVariant.query.filter(ProductVariant.label.ilike('%kivi%')).all()
        count = len(kivi_variants)
        
        if count == 0:
            return jsonify({"message": "No se encontraron variantes 'kivi' para eliminar"}), 200
        
        # Verificar cuáles están en uso
        in_use = []
        can_delete = []
        
        for v in kivi_variants:
            order_items_count = OrderItem.query.filter_by(variant_id=v.id).count()
            if order_items_count > 0:
                in_use.append((v.id, v.label, order_items_count))
            else:
                can_delete.append(v)
        
        # Eliminar solo las que no están en uso
        deleted_count = 0
        for v in can_delete:
            VariantPriceTier.query.filter_by(variant_id=v.id).delete()
            db.session.delete(v)
            deleted_count += 1
        
        db.session.commit()
        
        message = f"Se eliminaron {deleted_count} variante(s) 'kivi'"
        if in_use:
            in_use_details = ", ".join([f"'{label}' (en {count} pedido(s))" for _, label, count in in_use])
            message += f". No se pudieron eliminar {len(in_use)} variante(s) porque están en uso: {in_use_details}"
        
        return jsonify({
            "message": message,
            "deleted": deleted_count,
            "skipped": len(in_use)
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
