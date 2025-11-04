from flask import Blueprint, jsonify, request
from datetime import datetime
from ..db import db
from ..models.weekly_offer import WeeklyOffer
from ..models.product import Product
from .auth import require_token


weekly_offers_bp = Blueprint("weekly_offers", __name__)


@weekly_offers_bp.get("/weekly-offers")
def get_weekly_offers():
    """
    Obtiene las ofertas semanales vigentes según la fecha actual.
    Si hay ofertas con start_date, retorna las que están vigentes.
    Si no, retorna las más recientes.
    """
    from sqlalchemy import desc, case
    
    today = datetime.now()
    
    # Usar case para ordenar: ofertas con start_date primero, luego las sin fecha
    order_by_case = case(
        (WeeklyOffer.start_date.is_(None), 1),
        else_=0
    )
    
    # Obtener ofertas que estén vigentes hoy (start_date <= today y (end_date >= today o end_date es None))
    # Si no hay start_date, usar las más recientes como fallback
    try:
        fruta = WeeklyOffer.query.filter_by(type='fruta').filter(
            ((WeeklyOffer.start_date <= today) | (WeeklyOffer.start_date.is_(None))) &
            ((WeeklyOffer.end_date >= today) | (WeeklyOffer.end_date.is_(None)))
        ).order_by(order_by_case, desc(WeeklyOffer.start_date), desc(WeeklyOffer.updated_at)).first()
        
        verdura = WeeklyOffer.query.filter_by(type='verdura').filter(
            ((WeeklyOffer.start_date <= today) | (WeeklyOffer.start_date.is_(None))) &
            ((WeeklyOffer.end_date >= today) | (WeeklyOffer.end_date.is_(None)))
        ).order_by(order_by_case, desc(WeeklyOffer.start_date), desc(WeeklyOffer.updated_at)).first()
        
        especial = WeeklyOffer.query.filter_by(type='especial').filter(
            ((WeeklyOffer.start_date <= today) | (WeeklyOffer.start_date.is_(None))) &
            ((WeeklyOffer.end_date >= today) | (WeeklyOffer.end_date.is_(None)))
        ).order_by(order_by_case, desc(WeeklyOffer.start_date), desc(WeeklyOffer.updated_at)).first()
    except Exception:
        # Fallback: usar solo updated_at si hay error
        fruta = WeeklyOffer.query.filter_by(type='fruta').order_by(desc(WeeklyOffer.updated_at)).first()
        verdura = WeeklyOffer.query.filter_by(type='verdura').order_by(desc(WeeklyOffer.updated_at)).first()
        especial = WeeklyOffer.query.filter_by(type='especial').order_by(desc(WeeklyOffer.updated_at)).first()
    
    return jsonify({
        "fruta": fruta.to_dict() if fruta else None,
        "verdura": verdura.to_dict() if verdura else None,
        "especial": especial.to_dict() if especial else None
    })


@weekly_offers_bp.get("/weekly-offers/next-week")
@require_token
def get_next_week_offers():
    """
    Obtiene las ofertas semanales que estarán vigentes la próxima semana.
    Útil para planificación y generación de contenido con anticipación.
    """
    from sqlalchemy import desc, case
    from datetime import timedelta
    
    # Calcular el próximo lunes
    today = datetime.now()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)
    next_monday = next_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Usar case para ordenar: ofertas con start_date primero, luego las sin fecha
    order_by_case = case(
        (WeeklyOffer.start_date.is_(None), 1),
        else_=0
    )
    
    # Obtener ofertas que estarán vigentes el próximo lunes
    try:
        fruta = WeeklyOffer.query.filter_by(type='fruta').filter(
            ((WeeklyOffer.start_date <= next_monday) | (WeeklyOffer.start_date.is_(None))) &
            ((WeeklyOffer.end_date >= next_monday) | (WeeklyOffer.end_date.is_(None)))
        ).order_by(order_by_case, desc(WeeklyOffer.start_date), desc(WeeklyOffer.updated_at)).first()
        
        verdura = WeeklyOffer.query.filter_by(type='verdura').filter(
            ((WeeklyOffer.start_date <= next_monday) | (WeeklyOffer.start_date.is_(None))) &
            ((WeeklyOffer.end_date >= next_monday) | (WeeklyOffer.end_date.is_(None)))
        ).order_by(order_by_case, desc(WeeklyOffer.start_date), desc(WeeklyOffer.updated_at)).first()
        
        especial = WeeklyOffer.query.filter_by(type='especial').filter(
            ((WeeklyOffer.start_date <= next_monday) | (WeeklyOffer.start_date.is_(None))) &
            ((WeeklyOffer.end_date >= next_monday) | (WeeklyOffer.end_date.is_(None)))
        ).order_by(order_by_case, desc(WeeklyOffer.start_date), desc(WeeklyOffer.updated_at)).first()
    except Exception:
        # Fallback: usar solo updated_at si hay error
        fruta = WeeklyOffer.query.filter_by(type='fruta').order_by(desc(WeeklyOffer.updated_at)).first()
        verdura = WeeklyOffer.query.filter_by(type='verdura').order_by(desc(WeeklyOffer.updated_at)).first()
        especial = WeeklyOffer.query.filter_by(type='especial').order_by(desc(WeeklyOffer.updated_at)).first()
    
    return jsonify({
        "fruta": fruta.to_dict() if fruta else None,
        "verdura": verdura.to_dict() if verdura else None,
        "especial": especial.to_dict() if especial else None,
        "next_monday": next_monday.isoformat()
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
    
    # Parsear fechas si se proporcionan
    start_date = None
    end_date = None
    if data.get("start_date"):
        try:
            start_date = datetime.fromisoformat(data.get("start_date").replace('Z', '+00:00'))
        except:
            start_date = None
    if data.get("end_date"):
        try:
            end_date = datetime.fromisoformat(data.get("end_date").replace('Z', '+00:00'))
        except:
            end_date = None
    
    if existing:
        # Actualizar la existente
        existing.product_id = product_id
        existing.price = data.get("price", existing.price)
        existing.reference_price = data.get("reference_price", existing.reference_price)
        if start_date is not None:
            existing.start_date = start_date
        if end_date is not None:
            existing.end_date = end_date
        db.session.commit()
        return jsonify(existing.to_dict())
    else:
        # Crear nueva
        offer = WeeklyOffer(
            type=offer_type,
            product_id=product_id,
            price=data.get("price"),
            reference_price=data.get("reference_price"),
            start_date=start_date,
            end_date=end_date
        )
        db.session.add(offer)
        db.session.commit()
        return jsonify(offer.to_dict()), 201

