"""
Servicio para generar y enviar mensajes de WhatsApp
"""
from datetime import datetime, timedelta
import os

from ...db import db
from ...models.customer import Customer
from ..models.whatsapp_message import WhatsAppMessage


def generate_catalog_messages_batch(base_message_text=None):
    """
    Genera un batch de mensajes de catálogo para todos los clientes
    
    Args:
        base_message_text: Mensaje base personalizable. Si no se proporciona, usa el mensaje por defecto.
    """
    customers = Customer.query.filter(Customer.phone.isnot(None)).all()
    
    if not customers:
        return []
    
    # Mensaje base corto y conciso (puede ser personalizado)
    if base_message_text is None:
        november_offer = "🎉 ¡OFERTA NOVIEMBRE! Pide junto a un familiar o amigo y ambos obtienen 15% de descuento. Válido solo JUEVES y LUNES de noviembre. 🛒"
        base_message = f"📋 Catálogo de esta semana con ofertas vigentes\n\n{november_offer}"
    else:
        base_message = base_message_text
    
    messages = []
    
    # Programar para el próximo lunes a las 8:00 AM
    next_monday = get_next_monday()
    
    # URL del catálogo (se generará dinámicamente o será una URL estática)
    # Por ahora usamos una URL relativa que el frontend puede generar
    catalog_url = "/catalogo"  # URL relativa para generar el PDF
    
    for customer in customers:
        # Generar mensaje personalizado - usar nickname si existe, sino usar nombre completo
        customer_name = customer.nickname if customer.nickname else customer.name
        
        # Saludo personalizado basado en la personalidad del cliente
        greeting = "Hola"
        if customer.personality:
            # Si tiene personalidad definida, personalizar el saludo
            personality_lower = customer.personality.lower()
            if "formal" in personality_lower or "serio" in personality_lower:
                greeting = f"Hola {customer_name}"
            elif "amigable" in personality_lower or "cercano" in personality_lower:
                greeting = f"¡Hola {customer_name}! 👋"
            else:
                greeting = f"Hola {customer_name}"
        else:
            greeting = f"Hola {customer_name}"
        
        # Mensaje corto con catálogo
        message_text = f"""{greeting}

{base_message}

¡Esperamos tu pedido! 😊"""
        
        # Crear mensaje de WhatsApp
        message = WhatsAppMessage(
            customer_id=customer.id,
            message_type="catalog_offer",
            status="pending_approval",
            message_text=message_text,
            catalog_url=catalog_url,
            scheduled_date=next_monday
        )
        
        db.session.add(message)
        messages.append(message)
    
    db.session.commit()
    return messages


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


def send_whatsapp_message(message_id):
    """
    Envía un mensaje de WhatsApp usando la API configurada
    """
    message = WhatsAppMessage.query.get(message_id)
    if not message:
        return None
    
    if message.status != "approved":
        return None
    
    # TODO: Implementar envío real usando WhatsApp Business API
    # Por ahora solo marca como enviado
    message.status = "sent"
    message.sent_date = datetime.now()
    db.session.commit()
    
    return message

