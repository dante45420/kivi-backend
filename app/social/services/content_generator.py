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
    print(f"Generando carrusel para próxima semana - próximo lunes: {next_monday}")
    
    # Verificar si las columnas de fecha existen
    has_dates = _has_date_columns()
    print(f"Columnas de fecha disponibles: {has_dates}")
    
    def get_offer(type_name):
        """Obtiene una oferta del tipo especificado - prioriza las con fecha y la más reciente"""
        print(f"Buscando oferta tipo: {type_name} para próximo lunes: {next_monday}")
        if has_dates:
            try:
                # Primero: buscar ofertas que estarán vigentes el próximo lunes (próxima semana)
                offers_for_next_week = WeeklyOffer.query.filter_by(type=type_name).filter(
                    WeeklyOffer.start_date.isnot(None),
                    WeeklyOffer.start_date <= next_monday
                ).all()
                
                print(f"  Encontradas {len(offers_for_next_week)} ofertas con start_date <= próximo_lunes")
                
                # Filtrar las que estarán vigentes el próximo lunes
                valid_offers = []
                for offer in offers_for_next_week:
                    is_valid = offer.end_date is None or offer.end_date >= next_monday
                    print(f"  Oferta ID={offer.id}: start={offer.start_date}, end={offer.end_date}, válida={is_valid}")
                    if is_valid:
                        valid_offers.append(offer)
                
                # Si hay ofertas válidas para próxima semana, retornar la más reciente
                if valid_offers:
                    valid_offers.sort(key=lambda x: x.updated_at, reverse=True)
                    selected = valid_offers[0]
                    print(f"  ✓ Seleccionada oferta ID={selected.id} para próxima semana (más reciente de {len(valid_offers)} válidas)")
                    return selected
                
                # Si no hay ofertas para próxima semana, buscar ofertas de esta semana que aún estén vigentes
                print(f"  No hay ofertas para próxima semana, buscando ofertas de esta semana...")
                today = datetime.now()
                # Calcular lunes de esta semana
                days_since_monday = today.weekday()
                this_monday = today - timedelta(days=days_since_monday)
                this_monday = this_monday.replace(hour=0, minute=0, second=0, microsecond=0)
                this_sunday = this_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
                
                offers_for_this_week = WeeklyOffer.query.filter_by(type=type_name).filter(
                    WeeklyOffer.start_date.isnot(None),
                    WeeklyOffer.start_date <= this_sunday,
                    WeeklyOffer.end_date >= this_monday
                ).all()
                
                print(f"  Encontradas {len(offers_for_this_week)} ofertas para esta semana")
                
                if offers_for_this_week:
                    # Filtrar las que aún están vigentes hoy
                    current_week_valid = []
                    for offer in offers_for_this_week:
                        is_valid_today = offer.start_date <= today and (offer.end_date is None or offer.end_date >= today)
                        if is_valid_today:
                            current_week_valid.append(offer)
                    
                    if current_week_valid:
                        current_week_valid.sort(key=lambda x: x.updated_at, reverse=True)
                        selected = current_week_valid[0]
                        print(f"  ✓ Seleccionada oferta ID={selected.id} de esta semana (más reciente de {len(current_week_valid)} válidas)")
                        return selected
                
                print(f"  ✗ No hay ofertas válidas con fecha para {type_name}")
                return None
            except Exception as e:
                print(f"Error usando columnas de fecha: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        # Si no hay columnas de fecha, retornar la más reciente (comportamiento antiguo)
        offer = WeeklyOffer.query.filter_by(type=type_name).order_by(desc(WeeklyOffer.updated_at)).first()
        if offer:
            print(f"  ✓ Usando oferta sin fecha ID={offer.id} (comportamiento antiguo)")
        else:
            print(f"  ✗ No hay ofertas para {type_name}")
        return offer
    
    fruta = get_offer('fruta')
    verdura = get_offer('verdura')
    especial = get_offer('especial')
    
    print(f"Resultado: fruta={fruta is not None}, verdura={verdura is not None}, especial={especial is not None}")
    
    if not fruta or not verdura or not especial:
        print("❌ No se pueden generar ofertas - faltan una o más ofertas")
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
            print(f"✅ Imagen generada encontrada: {filename} -> {image_url}")
        else:
            print(f"⚠️ Imagen generada no encontrada: {generated_image_path}")
        
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
            print(f"✅ Imagen generada encontrada: {filename} -> {image_url}")
        else:
            print(f"⚠️ Imagen generada no encontrada: {generated_image_path}")
        
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
            print(f"✅ Imagen generada encontrada: {filename} -> {image_url}")
        else:
            print(f"⚠️ Imagen generada no encontrada: {generated_image_path}")
        
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

