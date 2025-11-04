from flask import Blueprint, jsonify, request
from datetime import datetime
from ..db import db
from ..models.weekly_offer import WeeklyOffer
from ..models.product import Product
from .auth import require_token
from sqlalchemy import inspect, desc
import traceback


weekly_offers_bp = Blueprint("weekly_offers", __name__)


def _has_date_columns():
    """Verifica si las columnas start_date y end_date existen en la tabla weekly_offers"""
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('weekly_offers')]
        return 'start_date' in columns and 'end_date' in columns
    except Exception as e:
        print(f"Error verificando columnas: {e}")
        return False


@weekly_offers_bp.get("/weekly-offers")
def get_weekly_offers():
    """
    Obtiene las ofertas semanales vigentes según la fecha actual.
    Si hay ofertas con start_date, retorna las que están vigentes.
    Si no, retorna las más recientes.
    """
    try:
        today = datetime.now()
        has_dates = _has_date_columns()
        
        def get_offer(type_name):
            # Si las columnas de fecha existen, intentar usarlas
            if has_dates:
                try:
                    # Intentar obtener oferta con start_date vigente
                    offer_with_date = WeeklyOffer.query.filter_by(type=type_name).filter(
                        WeeklyOffer.start_date.isnot(None),
                        WeeklyOffer.start_date <= today
                    ).order_by(desc(WeeklyOffer.start_date), desc(WeeklyOffer.updated_at)).first()
                    
                    if offer_with_date:
                        # Verificar si también tiene end_date y si está vigente
                        if offer_with_date.end_date is None or offer_with_date.end_date >= today:
                            return offer_with_date
                except Exception as e:
                    # Si falla al usar las columnas, continuar sin ellas
                    print(f"Error usando columnas de fecha: {e}")
            
            # Si no hay oferta con fecha vigente, usar la más reciente
            return WeeklyOffer.query.filter_by(type=type_name).order_by(desc(WeeklyOffer.updated_at)).first()
        
        fruta = get_offer('fruta')
        verdura = get_offer('verdura')
        especial = get_offer('especial')
        
        return jsonify({
            "fruta": fruta.to_dict() if fruta else None,
            "verdura": verdura.to_dict() if verdura else None,
            "especial": especial.to_dict() if especial else None
        })
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error en get_weekly_offers: {error_trace}")
        # Fallback simple: retornar las más recientes sin filtros de fecha
        try:
            fruta = WeeklyOffer.query.filter_by(type='fruta').order_by(desc(WeeklyOffer.updated_at)).first()
            verdura = WeeklyOffer.query.filter_by(type='verdura').order_by(desc(WeeklyOffer.updated_at)).first()
            especial = WeeklyOffer.query.filter_by(type='especial').order_by(desc(WeeklyOffer.updated_at)).first()
            return jsonify({
                "fruta": fruta.to_dict() if fruta else None,
                "verdura": verdura.to_dict() if verdura else None,
                "especial": especial.to_dict() if especial else None
            })
        except Exception as e2:
            print(f"Error en fallback: {e2}")
            return jsonify({"error": "Error al obtener ofertas", "details": str(e)}), 500


@weekly_offers_bp.get("/weekly-offers/next-week")
@require_token
def get_next_week_offers():
    """
    Obtiene las ofertas semanales que estarán vigentes la próxima semana.
    Útil para planificación y generación de contenido con anticipación.
    """
    from datetime import timedelta
    
    try:
        # Calcular el próximo lunes
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)
        next_monday = next_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        has_dates = _has_date_columns()
        
        def get_offer(type_name):
            # Si las columnas de fecha existen, intentar usarlas
            if has_dates:
                try:
                    # Intentar obtener oferta con start_date que esté vigente el próximo lunes
                    offer_with_date = WeeklyOffer.query.filter_by(type=type_name).filter(
                        WeeklyOffer.start_date.isnot(None),
                        WeeklyOffer.start_date <= next_monday
                    ).order_by(desc(WeeklyOffer.start_date), desc(WeeklyOffer.updated_at)).first()
                    
                    if offer_with_date:
                        # Verificar si también tiene end_date y si está vigente
                        if offer_with_date.end_date is None or offer_with_date.end_date >= next_monday:
                            return offer_with_date
                except Exception as e:
                    # Si falla al usar las columnas, continuar sin ellas
                    print(f"Error usando columnas de fecha: {e}")
            
            # Si no hay oferta con fecha, usar la más reciente
            return WeeklyOffer.query.filter_by(type=type_name).order_by(desc(WeeklyOffer.updated_at)).first()
        
        fruta = get_offer('fruta')
        verdura = get_offer('verdura')
        especial = get_offer('especial')
        
        return jsonify({
            "fruta": fruta.to_dict() if fruta else None,
            "verdura": verdura.to_dict() if verdura else None,
            "especial": especial.to_dict() if especial else None,
            "next_monday": next_monday.isoformat()
        })
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error en get_next_week_offers: {error_trace}")
        # Fallback simple
        try:
            fruta = WeeklyOffer.query.filter_by(type='fruta').order_by(desc(WeeklyOffer.updated_at)).first()
            verdura = WeeklyOffer.query.filter_by(type='verdura').order_by(desc(WeeklyOffer.updated_at)).first()
            especial = WeeklyOffer.query.filter_by(type='especial').order_by(desc(WeeklyOffer.updated_at)).first()
            return jsonify({
                "fruta": fruta.to_dict() if fruta else None,
                "verdura": verdura.to_dict() if verdura else None,
                "especial": especial.to_dict() if especial else None,
                "next_monday": None
            })
        except Exception as e2:
            return jsonify({"error": "Error al obtener ofertas", "details": str(e)}), 500


@weekly_offers_bp.post("/weekly-offers")
@require_token
def create_or_update_weekly_offer():
    """Crea o actualiza una oferta semanal y actualiza la foto del producto si se proporciona"""
    from datetime import timedelta
    
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
    
    # Determinar para qué semana es la oferta
    week_target = data.get("week_target", "current")  # "current" o "next"
    
    # Calcular fechas de la semana
    today = datetime.now()
    
    # Calcular lunes de esta semana
    days_since_monday = today.weekday()  # 0 = lunes, 6 = domingo
    this_monday = today - timedelta(days=days_since_monday)
    this_monday = this_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if week_target == "next":
        # Para próxima semana: lunes de la próxima semana
        week_monday = this_monday + timedelta(days=7)
    else:
        # Para esta semana: lunes de esta semana
        week_monday = this_monday
    
    week_sunday = week_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    # Parsear fechas si se proporcionan explícitamente
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
    
    # Si no se proporcionaron fechas, usar las calculadas automáticamente
    if start_date is None:
        start_date = week_monday
    if end_date is None:
        end_date = week_sunday
    
    has_dates = _has_date_columns()
    
    # Buscar si ya existe una oferta de este tipo para esta semana
    existing = None
    if has_dates:
        try:
            # Buscar ofertas que se solapen con esta semana
            existing = WeeklyOffer.query.filter_by(type=offer_type).filter(
                WeeklyOffer.start_date <= week_sunday,
                WeeklyOffer.end_date >= week_monday
            ).first()
            
            # Si no hay solapamiento, buscar la más reciente
            if not existing:
                existing = WeeklyOffer.query.filter_by(type=offer_type).order_by(
                    WeeklyOffer.updated_at.desc()
                ).first()
        except Exception:
            # Fallback: buscar la más reciente
            existing = WeeklyOffer.query.filter_by(type=offer_type).order_by(
                WeeklyOffer.updated_at.desc()
            ).first()
    else:
        existing = WeeklyOffer.query.filter_by(type=offer_type).order_by(
            WeeklyOffer.updated_at.desc()
        ).first()
    
    if existing:
        # Actualizar la existente
        existing.product_id = product_id
        existing.price = data.get("price", existing.price)
        existing.reference_price = data.get("reference_price", existing.reference_price)
        if has_dates:
            existing.start_date = start_date
            existing.end_date = end_date
        db.session.commit()
        return jsonify(existing.to_dict())
    else:
        # Crear nueva
        offer_data = {
            "type": offer_type,
            "product_id": product_id,
            "price": data.get("price"),
            "reference_price": data.get("reference_price")
        }
        if has_dates:
            offer_data["start_date"] = start_date
            offer_data["end_date"] = end_date
        
        offer = WeeklyOffer(**offer_data)
        db.session.add(offer)
        db.session.commit()
        return jsonify(offer.to_dict()), 201

