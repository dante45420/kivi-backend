"""
Servicio para generar contenido automático de Instagram
"""
from datetime import datetime, timedelta
import json
import os

from ...db import db
from ...models.weekly_offer import WeeklyOffer
from ..models.instagram_content import InstagramContent
from ..models.content_template import ContentTemplate
from sqlalchemy import inspect, desc


def _has_date_columns():
    """Verifica si las columnas start_date y end_date existen en la tabla weekly_offers"""
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('weekly_offers')]
        return 'start_date' in columns and 'end_date' in columns
    except Exception as e:
        print(f"Error verificando columnas: {e}")
        return False


def generate_weekly_offers_carousel():
    """
    Genera un carrusel de Instagram con las 3 ofertas semanales de la PRÓXIMA semana
    """
    # Calcular el próximo lunes (fecha de publicación)
    next_monday = get_next_monday()
    
    # Verificar si las columnas de fecha existen
    has_dates = _has_date_columns()
    
    def get_offer(type_name):
        """Obtiene una oferta del tipo especificado - prioriza las con fecha y la más reciente"""
        if has_dates:
            try:
                # Buscar todas las ofertas con fecha que estén vigentes el próximo lunes
                offers_with_date = WeeklyOffer.query.filter_by(type=type_name).filter(
                    WeeklyOffer.start_date.isnot(None),
                    WeeklyOffer.start_date <= next_monday
                ).all()
                
                # Filtrar las que estarán vigentes el próximo lunes
                valid_offers = []
                for offer in offers_with_date:
                    if offer.end_date is None or offer.end_date >= next_monday:
                        valid_offers.append(offer)
                
                # Si hay ofertas válidas con fecha, retornar la más reciente
                if valid_offers:
                    valid_offers.sort(key=lambda x: x.updated_at, reverse=True)
                    return valid_offers[0]
                
                # Si no hay ofertas con fecha, retornar None (no usar las sin fecha)
                return None
            except Exception as e:
                print(f"Error usando columnas de fecha: {e}")
                return None
        
        # Si no hay columnas de fecha, retornar la más reciente (comportamiento antiguo)
        return WeeklyOffer.query.filter_by(type=type_name).order_by(desc(WeeklyOffer.updated_at)).first()
    
    fruta = get_offer('fruta')
    verdura = get_offer('verdura')
    especial = get_offer('especial')
    
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
    
    # Generar imágenes usando la plantilla
    from ..utils.image_processor import generate_offer_image
    
    # URLs de imágenes para cada slide del carrusel con descripciones editables
    media_urls = []
    
    # Slide 1: Verdura
    if verdura.product and verdura.product.quality_photo_url:
        # Generar imagen usando la plantilla
        generated_image_path = generate_offer_image(
            offer_type='verdura',
            product_name=verdura.product.name,
            price=verdura.price or "",
            reference_price=verdura.reference_price or "",
            product_image_url=verdura.product.quality_photo_url
        )
        
        # Usar la imagen generada si existe, sino usar la original
        image_url = verdura.product.quality_photo_url
        if generated_image_path and os.path.exists(generated_image_path):
            # Convertir la ruta local a una URL accesible
            filename = os.path.basename(generated_image_path)
            image_url = f"/api/social/instagram/generated-image/{filename}"
        
        media_urls.append({
            "type": "image",
            "url": image_url,
            "offer_type": "verdura",
            "product_name": verdura.product.name,
            "price": verdura.price or "",
            "reference_price": verdura.reference_price or "",
            "default_caption": f"🥬 {verdura.product.name}\n{verdura.price or ''}\n{verdura.reference_price if verdura.reference_price else ''}",
            "caption": f"🥬 {verdura.product.name}\n{verdura.price or ''}\n{verdura.reference_price if verdura.reference_price else ''}"  # Editable
        })
    
    # Slide 2: Fruta
    if fruta.product and fruta.product.quality_photo_url:
        # Generar imagen usando la plantilla
        generated_image_path = generate_offer_image(
            offer_type='fruta',
            product_name=fruta.product.name,
            price=fruta.price or "",
            reference_price=fruta.reference_price or "",
            product_image_url=fruta.product.quality_photo_url
        )
        
        # Usar la imagen generada si existe, sino usar la original
        image_url = fruta.product.quality_photo_url
        if generated_image_path and os.path.exists(generated_image_path):
            # Convertir la ruta local a una URL accesible
            filename = os.path.basename(generated_image_path)
            image_url = f"/api/social/instagram/generated-image/{filename}"
        
        media_urls.append({
            "type": "image",
            "url": image_url,
            "offer_type": "fruta",
            "product_name": fruta.product.name,
            "price": fruta.price or "",
            "reference_price": fruta.reference_price or "",
            "default_caption": f"🍎 {fruta.product.name}\n{fruta.price or ''}\n{fruta.reference_price if fruta.reference_price else ''}",
            "caption": f"🍎 {fruta.product.name}\n{fruta.price or ''}\n{fruta.reference_price if fruta.reference_price else ''}"  # Editable
        })
    
    # Slide 3: Especial
    if especial.product and especial.product.quality_photo_url:
        # Generar imagen usando la plantilla
        generated_image_path = generate_offer_image(
            offer_type='especial',
            product_name=especial.product.name,
            price=especial.price or "",
            reference_price=especial.reference_price or "",
            product_image_url=especial.product.quality_photo_url
        )
        
        # Usar la imagen generada si existe, sino usar la original
        image_url = especial.product.quality_photo_url
        if generated_image_path and os.path.exists(generated_image_path):
            # Convertir la ruta local a una URL accesible
            filename = os.path.basename(generated_image_path)
            image_url = f"/api/social/instagram/generated-image/{filename}"
        
        media_urls.append({
            "type": "image",
            "url": image_url,
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

