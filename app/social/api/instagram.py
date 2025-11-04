from flask import Blueprint, jsonify, request, send_file
import json
import os

from ...db import db
from ...api.auth import require_token
from ..models.instagram_content import InstagramContent
from ..models.content_template import ContentTemplate
from ..utils.image_positions import get_positions, save_positions


instagram_bp = Blueprint("instagram", __name__)


@instagram_bp.get("/instagram/content")
@require_token
def list_instagram_content():
    """Lista contenido de Instagram con filtros opcionales"""
    status = request.args.get('status')
    content_type = request.args.get('type')
    
    query = InstagramContent.query
    
    if status:
        query = query.filter_by(status=status)
    if content_type:
        query = query.filter_by(type=content_type)
    
    content_list = query.order_by(InstagramContent.created_at.desc()).all()
    return jsonify([c.to_dict() for c in content_list])


@instagram_bp.get("/instagram/content/<int:content_id>")
@require_token
def get_instagram_content(content_id):
    """Obtiene un contenido específico de Instagram"""
    content = InstagramContent.query.get(content_id)
    if not content:
        return jsonify({"error": "Contenido no encontrado"}), 404
    return jsonify(content.to_dict())


@instagram_bp.post("/instagram/content")
@require_token
def create_instagram_content():
    """Crea un nuevo contenido de Instagram"""
    data = request.get_json(silent=True) or {}
    
    content = InstagramContent(
        type=data.get("type", "post"),
        template_type=data.get("template_type"),
        status=data.get("status", "draft"),
        content_data=json.dumps(data.get("content_data", {})),
        media_urls=json.dumps(data.get("media_urls", []))
    )
    
    db.session.add(content)
    db.session.commit()
    return jsonify(content.to_dict()), 201


@instagram_bp.post("/instagram/generate")
@require_token
def generate_instagram_content():
    """Genera contenido automático de Instagram"""
    try:
        data = request.get_json(silent=True) or {}
        content_type = data.get("type", "ofertas_semana")
        
        from ..services.content_generator import generate_weekly_offers_carousel, generate_content_from_template
        
        if content_type == "ofertas_semana":
            content = generate_weekly_offers_carousel()
            if not content:
                return jsonify({"error": "No se pudieron generar las ofertas. Verifica que existan las 3 ofertas semanales."}), 400
            return jsonify(content.to_dict()), 201
        else:
            content = generate_content_from_template(content_type)
            if not content:
                return jsonify({"error": "No se pudo generar el contenido"}), 400
            return jsonify(content.to_dict()), 201
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error generando contenido de Instagram: {error_details}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500


@instagram_bp.patch("/instagram/content/<int:content_id>/approve")
@require_token
def approve_instagram_content(content_id):
    """Aprueba un contenido de Instagram"""
    content = InstagramContent.query.get(content_id)
    if not content:
        return jsonify({"error": "Contenido no encontrado"}), 404
    
    content.status = 'approved'
    db.session.commit()
    return jsonify(content.to_dict())


@instagram_bp.patch("/instagram/content/<int:content_id>/reject")
@require_token
def reject_instagram_content(content_id):
    """Rechaza un contenido de Instagram"""
    data = request.get_json(silent=True) or {}
    content = InstagramContent.query.get(content_id)
    if not content:
        return jsonify({"error": "Contenido no encontrado"}), 404
    
    content.status = 'rejected'
    content.rejection_reason = data.get("rejection_reason")
    db.session.commit()
    return jsonify(content.to_dict())


@instagram_bp.patch("/instagram/content/<int:content_id>")
@require_token
def update_instagram_content(content_id):
    """Actualiza el contenido de Instagram (descripciones, captions, etc.)"""
    data = request.get_json(silent=True) or {}
    content = InstagramContent.query.get(content_id)
    if not content:
        return jsonify({"error": "Contenido no encontrado"}), 404
    
    # Actualizar content_data si se proporciona
    if "content_data" in data:
        content.content_data = json.dumps(data["content_data"])
    
    # Actualizar media_urls si se proporciona (para editar captions de slides)
    if "media_urls" in data:
        content.media_urls = json.dumps(data["media_urls"])
    
    # Actualizar full_text si cambió la descripción
    if "content_data" in data:
        content_data = data["content_data"]
        hashtags = content_data.get("hashtags", [])
        description = content_data.get("description", "")
        if isinstance(hashtags, list):
            content_data["full_text"] = f"{description}\n\n{' '.join(hashtags)}"
        content.content_data = json.dumps(content_data)
    
    db.session.commit()
    return jsonify(content.to_dict())


@instagram_bp.get("/instagram/templates")
@require_token
def list_templates():
    """Lista todos los templates de contenido"""
    templates = ContentTemplate.query.filter_by(is_active=True).all()
    return jsonify([t.to_dict() for t in templates])


@instagram_bp.post("/instagram/templates")
@require_token
def create_template():
    """Crea o actualiza un template de contenido"""
    data = request.get_json(silent=True) or {}
    
    name = data.get("name")
    if not name:
        return jsonify({"error": "name es requerido"}), 400
    
    existing = ContentTemplate.query.filter_by(name=name).first()
    
    if existing:
        # Actualizar existente
        existing.template_type = data.get("template_type", existing.template_type)
        existing.content_structure = json.dumps(data.get("content_structure", {}))
        existing.default_hashtags = json.dumps(data.get("default_hashtags", []))
        existing.color_palette = json.dumps(data.get("color_palette", {}))
        existing.is_active = data.get("is_active", existing.is_active)
        db.session.commit()
        return jsonify(existing.to_dict())
    else:
        # Crear nuevo
        template = ContentTemplate(
            name=name,
            template_type=data.get("template_type", "post"),
            content_structure=json.dumps(data.get("content_structure", {})),
            default_hashtags=json.dumps(data.get("default_hashtags", [])),
            color_palette=json.dumps(data.get("color_palette", {}))
        )
        db.session.add(template)
        db.session.commit()
        return jsonify(template.to_dict()), 201


@instagram_bp.get("/instagram/image-positions")
@require_token
def get_image_positions():
    """Obtiene las posiciones configuradas para las imágenes de ofertas"""
    return jsonify(get_positions())


@instagram_bp.post("/instagram/image-positions")
@require_token
def update_image_positions():
    """Actualiza las posiciones de los elementos en la plantilla de ofertas"""
    data = request.get_json(silent=True) or {}
    
    if save_positions(data):
        return jsonify({"success": True, "positions": get_positions()})
    else:
        return jsonify({"error": "No se pudieron guardar las posiciones"}), 500

