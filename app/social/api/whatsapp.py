from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta

from ...db import db
from ...api.auth import require_token
from ...models.customer import Customer
from ..models.whatsapp_message import WhatsAppMessage


whatsapp_bp = Blueprint("whatsapp", __name__)


@whatsapp_bp.get("/whatsapp/messages")
@require_token
def list_whatsapp_messages():
    """Lista mensajes de WhatsApp con filtros opcionales"""
    status = request.args.get('status')
    message_type = request.args.get('message_type')
    
    query = WhatsAppMessage.query
    
    if status:
        query = query.filter_by(status=status)
    if message_type:
        query = query.filter_by(message_type=message_type)
    
    messages = query.order_by(WhatsAppMessage.created_at.desc()).all()
    return jsonify([m.to_dict() for m in messages])


@whatsapp_bp.get("/whatsapp/messages/<int:message_id>")
@require_token
def get_whatsapp_message(message_id):
    """Obtiene un mensaje específico de WhatsApp"""
    message = WhatsAppMessage.query.get(message_id)
    if not message:
        return jsonify({"error": "Mensaje no encontrado"}), 404
    return jsonify(message.to_dict())


@whatsapp_bp.get("/whatsapp/preview/<int:customer_id>")
@require_token
def preview_whatsapp_message(customer_id):
    """Genera un preview del mensaje para un cliente específico"""
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Cliente no encontrado"}), 404
    
    from ..services.whatsapp_sender import generate_catalog_messages_batch
    
    # Generar preview del mensaje
    customer_name = customer.nickname or customer.name.split()[0]
    greeting = "Hola"
    if customer.personality:
        personality_lower = customer.personality.lower()
        if "formal" in personality_lower or "serio" in personality_lower:
            greeting = f"Hola {customer_name}"
        elif "amigable" in personality_lower or "cercano" in personality_lower:
            greeting = f"¡Hola {customer_name}! 👋"
        else:
            greeting = f"Hola {customer_name}"
    else:
        greeting = f"Hola {customer_name}"
    
    november_offer = """🎉 ¡OFERTA ESPECIAL DE NOVIEMBRE! 🎉

Pide junto a un familiar, vecino o amigo y ambos obtienen un 15% de descuento.

✅ Válido solo los JUEVES y LUNES de noviembre
✅ Aplica para cualquier pedido
✅ El descuento se aplica automáticamente cuando mencionas que vienes acompañado

¡Aprovecha esta oportunidad única de ahorrar en tus compras favoritas! 🛒✨"""
    
    preview_text = f"""{greeting}

Te comparto el catálogo de esta semana con nuestras mejores ofertas. 📋

{november_offer}

¡Esperamos tu pedido! 😊"""
    
    return jsonify({
        "customer": customer.to_dict(),
        "preview": preview_text
    })


@whatsapp_bp.post("/whatsapp/generate-catalog-batch")
@require_token
def generate_catalog_batch():
    """Genera un batch de mensajes de catálogo para todos los clientes"""
    from ..services.whatsapp_sender import generate_catalog_messages_batch
    
    messages = generate_catalog_messages_batch()
    
    if not messages:
        return jsonify({"error": "No se encontraron clientes con teléfono"}), 400
    
    return jsonify({
        "message": f"Se generaron {len(messages)} mensajes",
        "messages": [m.to_dict() for m in messages]
    }), 201


@whatsapp_bp.patch("/whatsapp/message/<int:message_id>/approve")
@require_token
def approve_whatsapp_message(message_id):
    """Aprueba un mensaje de WhatsApp"""
    message = WhatsAppMessage.query.get(message_id)
    if not message:
        return jsonify({"error": "Mensaje no encontrado"}), 404
    
    message.status = 'approved'
    db.session.commit()
    return jsonify(message.to_dict())


@whatsapp_bp.patch("/whatsapp/message/<int:message_id>/reject")
@require_token
def reject_whatsapp_message(message_id):
    """Rechaza un mensaje de WhatsApp"""
    data = request.get_json(silent=True) or {}
    message = WhatsAppMessage.query.get(message_id)
    if not message:
        return jsonify({"error": "Mensaje no encontrado"}), 404
    
    message.status = 'rejected'
    db.session.commit()
    return jsonify(message.to_dict())


@whatsapp_bp.post("/whatsapp/send-test")
@require_token
def send_test_message():
    """Envía un mensaje de prueba de WhatsApp"""
    data = request.get_json(silent=True) or {}
    phone = data.get("phone")
    
    if not phone:
        return jsonify({"error": "phone es requerido"}), 400
    
    # TODO: Implementar envío de prueba
    return jsonify({"message": "Envío de prueba en desarrollo"}), 501

