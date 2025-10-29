from flask import Blueprint, jsonify, request
from ..db import db
from ..models.weekly_offer import WeeklyOffer
from ..models.product import Product
from .auth import require_token


weekly_offers_bp = Blueprint("weekly_offers", __name__)


@weekly_offers_bp.get("/weekly-offers")
def get_weekly_offers():
    """Obtiene las ofertas semanales actuales con información del producto"""
    # Obtener la oferta más reciente de cada tipo
    fruta = WeeklyOffer.query.filter_by(type='fruta').order_by(WeeklyOffer.updated_at.desc()).first()
    verdura = WeeklyOffer.query.filter_by(type='verdura').order_by(WeeklyOffer.updated_at.desc()).first()
    especial = WeeklyOffer.query.filter_by(type='especial').order_by(WeeklyOffer.updated_at.desc()).first()
    
    return jsonify({
        "fruta": fruta.to_dict() if fruta else None,
        "verdura": verdura.to_dict() if verdura else None,
        "especial": especial.to_dict() if especial else None
    })


@weekly_offers_bp.post("/weekly-offers")
@require_token
def create_or_update_weekly_offer():
    """Crea o actualiza una oferta semanal y actualiza la foto del producto si se proporciona"""
    data = request.get_json(silent=True) or {}
    
    offer_type = data.get("type")
    if offer_type not in ['fruta', 'verdura', 'especial']:
        return jsonify({"error": "type debe ser 'fruta', 'verdura' o 'especial'"}), 400
    
    product_id = data.get("product_id")
    if not product_id:
        return jsonify({"error": "product_id es requerido"}), 400
    
    # Verificar que el producto existe
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Producto no encontrado"}), 404
    
    # Actualizar foto del producto si se proporciona
    if "quality_photo_url" in data:
        product.quality_photo_url = data.get("quality_photo_url")
        db.session.flush()  # Guardar cambios del producto antes de continuar
    
    # Buscar si ya existe una oferta de este tipo
    existing = WeeklyOffer.query.filter_by(type=offer_type).order_by(WeeklyOffer.updated_at.desc()).first()
    
    if existing:
        # Actualizar la existente
        existing.product_id = product_id
        existing.price = data.get("price", existing.price)
        existing.reference_price = data.get("reference_price", existing.reference_price)
        db.session.commit()
        return jsonify(existing.to_dict())
    else:
        # Crear nueva
        offer = WeeklyOffer(
            type=offer_type,
            product_id=product_id,
            price=data.get("price"),
            reference_price=data.get("reference_price")
        )
        db.session.add(offer)
        db.session.commit()
        return jsonify(offer.to_dict()), 201

