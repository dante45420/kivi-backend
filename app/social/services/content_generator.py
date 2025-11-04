"""
Servicio para generar contenido automático de Instagram
"""
from datetime import datetime, timedelta
import json

from ...db import db
from ...models.weekly_offer import WeeklyOffer
from ..models.instagram_content import InstagramContent
from ..models.content_template import ContentTemplate


def generate_weekly_offers_carousel():
    """
    Genera un carrusel de Instagram con las 3 ofertas semanales de la PRÓXIMA semana
    """
    # Calcular el próximo lunes (fecha de publicación)
    next_monday = get_next_monday()
    
    # Obtener las ofertas que estarán vigentes el próximo lunes
    # Versión simplificada y robusta: primero intentar con fechas, luego sin fechas
    from sqlalchemy import desc
    
    # Intentar obtener ofertas con start_date que estén vigentes
    try:
        fruta = WeeklyOffer.query.filter_by(type='fruta').filter(
            WeeklyOffer.start_date.isnot(None),
            WeeklyOffer.start_date <= next_monday
        ).order_by(desc(WeeklyOffer.start_date), desc(WeeklyOffer.updated_at)).first()
        
        verdura = WeeklyOffer.query.filter_by(type='verdura').filter(
            WeeklyOffer.start_date.isnot(None),
            WeeklyOffer.start_date <= next_monday
        ).order_by(desc(WeeklyOffer.start_date), desc(WeeklyOffer.updated_at)).first()
        
        especial = WeeklyOffer.query.filter_by(type='especial').filter(
            WeeklyOffer.start_date.isnot(None),
            WeeklyOffer.start_date <= next_monday
        ).order_by(desc(WeeklyOffer.start_date), desc(WeeklyOffer.updated_at)).first()
        
        # Si no hay ofertas con fechas, usar las más recientes
        if not fruta:
            fruta = WeeklyOffer.query.filter_by(type='fruta').order_by(desc(WeeklyOffer.updated_at)).first()
        if not verdura:
            verdura = WeeklyOffer.query.filter_by(type='verdura').order_by(desc(WeeklyOffer.updated_at)).first()
        if not especial:
            especial = WeeklyOffer.query.filter_by(type='especial').order_by(desc(WeeklyOffer.updated_at)).first()
    except Exception:
        # Fallback completo: usar solo updated_at
        fruta = WeeklyOffer.query.filter_by(type='fruta').order_by(desc(WeeklyOffer.updated_at)).first()
        verdura = WeeklyOffer.query.filter_by(type='verdura').order_by(desc(WeeklyOffer.updated_at)).first()
        especial = WeeklyOffer.query.filter_by(type='especial').order_by(desc(WeeklyOffer.updated_at)).first()
    
    if not fruta or not verdura or not especial:
        return None
    
    # Descripción por defecto para el carrusel (editables)
    default_description = "🎉 ¡OFERTAS DE LA SEMANA! 🎉\n\nDesliza y descubre nuestras mejores ofertas en frutas y verduras frescas. ¡No te las pierdas! 🛒✨"
    
    # Hashtags base
    hashtags = [
        "#frutasfrescas",
        "#verdurasfrescas",
        "#ofertasdelasemana",
        "#kivi",
        "#saludable",
        "#comidalocal"
    ]
    
    # URLs de imágenes para cada slide del carrusel con descripciones editables
    media_urls = []
    
    # Slide 1: Verdura
    if verdura.product and verdura.product.quality_photo_url:
        media_urls.append({
            "type": "image",
            "url": verdura.product.quality_photo_url,
            "offer_type": "verdura",
            "product_name": verdura.product.name,
            "price": verdura.price or "",
            "reference_price": verdura.reference_price or "",
            "default_caption": f"🥬 {verdura.product.name}\n{verdura.price or ''}\n{verdura.reference_price if verdura.reference_price else ''}",
            "caption": f"🥬 {verdura.product.name}\n{verdura.price or ''}\n{verdura.reference_price if verdura.reference_price else ''}"  # Editable
        })
    
    # Slide 2: Fruta
    if fruta.product and fruta.product.quality_photo_url:
        media_urls.append({
            "type": "image",
            "url": fruta.product.quality_photo_url,
            "offer_type": "fruta",
            "product_name": fruta.product.name,
            "price": fruta.price or "",
            "reference_price": fruta.reference_price or "",
            "default_caption": f"🍎 {fruta.product.name}\n{fruta.price or ''}\n{fruta.reference_price if fruta.reference_price else ''}",
            "caption": f"🍎 {fruta.product.name}\n{fruta.price or ''}\n{fruta.reference_price if fruta.reference_price else ''}"  # Editable
        })
    
    # Slide 3: Especial
    if especial.product and especial.product.quality_photo_url:
        media_urls.append({
            "type": "image",
            "url": especial.product.quality_photo_url,
            "offer_type": "especial",
            "product_name": especial.product.name,
            "price": especial.price or "",
            "reference_price": especial.reference_price or "",
            "default_caption": f"⭐ {especial.product.name}\n{especial.price or ''}\n{especial.reference_price if especial.reference_price else ''}",
            "caption": f"⭐ {especial.product.name}\n{especial.price or ''}\n{especial.reference_price if especial.reference_price else ''}"  # Editable
        })
    
    if not media_urls:
        return None
    
    # Crear el contenido de Instagram con estructura editable
    content_data = {
        "default_description": default_description,
        "description": default_description,  # Editable
        "hashtags": hashtags,
        "full_text": f"{default_description}\n\n{' '.join(hashtags)}"
    }
    
    content = InstagramContent(
        type="carousel",
        template_type="ofertas_semana",
        status="pending_approval",
        content_data=json.dumps(content_data),
        media_urls=json.dumps(media_urls),
        scheduled_date=next_monday
    )
    
    db.session.add(content)
    db.session.commit()
    
    return content


def get_next_monday():
    """Calcula el próximo lunes a las 8:00 AM"""
    today = datetime.now()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        # Si ya es lunes, programar para el próximo lunes
        days_until_monday = 7
    
    next_monday = today + timedelta(days=days_until_monday)
    next_monday = next_monday.replace(hour=8, minute=0, second=0, microsecond=0)
    return next_monday


def generate_content_from_template(template_name, **kwargs):
    """
    Genera contenido de Instagram desde un template
    """
    template = ContentTemplate.query.filter_by(name=template_name, is_active=True).first()
    if not template:
        return None
    
    # TODO: Implementar lógica de generación según el template
    # Por ahora retorna None
    return None

