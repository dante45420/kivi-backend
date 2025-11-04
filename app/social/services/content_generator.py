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
    Genera un carrusel de Instagram con las 3 ofertas semanales
    """
    # Obtener las ofertas semanales
    fruta = WeeklyOffer.query.filter_by(type='fruta').order_by(WeeklyOffer.updated_at.desc()).first()
    verdura = WeeklyOffer.query.filter_by(type='verdura').order_by(WeeklyOffer.updated_at.desc()).first()
    especial = WeeklyOffer.query.filter_by(type='especial').order_by(WeeklyOffer.updated_at.desc()).first()
    
    if not fruta or not verdura or not especial:
        return None
    
    # Descripción constante para el carrusel
    description = "🎉 ¡OFERTAS DE LA SEMANA! 🎉\n\nDesliza y descubre nuestras mejores ofertas en frutas y verduras frescas. ¡No te las pierdas! 🛒✨"
    
    # Hashtags base
    hashtags = [
        "#frutasfrescas",
        "#verdurasfrescas",
        "#ofertasdelasemana",
        "#kivi",
        "#saludable",
        "#comidalocal"
    ]
    
    # URLs de imágenes para cada slide del carrusel
    media_urls = []
    
    # Slide 1: Verdura
    if verdura.product and verdura.product.quality_photo_url:
        media_urls.append({
            "type": "image",
            "url": verdura.product.quality_photo_url,
            "caption": f"🥬 {verdura.product.name}\n{verdura.price}\n{verdura.reference_price if verdura.reference_price else ''}"
        })
    
    # Slide 2: Fruta
    if fruta.product and fruta.product.quality_photo_url:
        media_urls.append({
            "type": "image",
            "url": fruta.product.quality_photo_url,
            "caption": f"🍎 {fruta.product.name}\n{fruta.price}\n{fruta.reference_price if fruta.reference_price else ''}"
        })
    
    # Slide 3: Especial
    if especial.product and especial.product.quality_photo_url:
        media_urls.append({
            "type": "image",
            "url": especial.product.quality_photo_url,
            "caption": f"⭐ {especial.product.name}\n{especial.price}\n{especial.reference_price if especial.reference_price else ''}"
        })
    
    if not media_urls:
        return None
    
    # Crear el contenido de Instagram
    content_data = {
        "description": description,
        "hashtags": hashtags,
        "full_text": f"{description}\n\n{' '.join(hashtags)}"
    }
    
    # Programar para el próximo lunes a las 8:00 AM
    next_monday = get_next_monday()
    
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

