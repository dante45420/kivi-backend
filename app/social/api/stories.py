"""
API para gestión de historias de Instagram
Endpoints para generar, aprobar, rechazar y programar historias
"""
from flask import Blueprint, request, jsonify, send_file
from datetime import datetime, timedelta
import json
import uuid
import os

from ...db import db
from ...models.product import Product
from ..models import StoryTemplate, StoryContent, StoryGeneration
from ..services.story_content_generator import StoryContentGenerator
from ..services.story_image_generator import StoryImageGenerator
from ..services.story_video_generator import StoryVideoGenerator
from ..services.story_scheduler import StoryScheduler

stories_bp = Blueprint('stories', __name__, url_prefix='/api/social/stories')

# Inicializar generadores de forma lazy para evitar crashes si falta config
content_gen = None
image_gen = None
video_gen = None
scheduler = None

def get_generators():
    """Inicializa los generadores solo cuando se necesitan"""
    global content_gen, image_gen, video_gen, scheduler
    
    if content_gen is None:
        content_gen = StoryContentGenerator()
    if image_gen is None:
        image_gen = StoryImageGenerator()
    if video_gen is None:
        video_gen = StoryVideoGenerator()
    if scheduler is None:
        scheduler = StoryScheduler()
    
    return content_gen, image_gen, video_gen, scheduler


@stories_bp.route('/health', methods=['GET'])
def health_check():
    """Verifica la configuración del sistema de historias"""
    import os
    
    config_status = {
        "openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
        "ffmpeg_available": False,
        "ready": False
    }
    
    # Verificar FFmpeg
    try:
        import subprocess
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        config_status["ffmpeg_available"] = True
    except:
        pass
    
    config_status["ready"] = config_status["openai_api_key"]
    
    return jsonify(config_status), 200


@stories_bp.route('/generate-batch', methods=['POST'])
def generate_batch():
    """
    Genera un batch de historias para una semana específica
    
    Body (opcional):
    {
        "count": 8,  # Cantidad a generar (default: 8)
        "target_week": "2025-11-11",  # Lunes de la semana (default: próxima semana)
        "themes": ["tip_semana", "doggo_prueba"],  # Temas específicos (opcional)
        "content_types": ["image", "video"],  # Tipos de contenido (opcional)
        "force_regenerate": false  # Regenerar aunque ya existan (default: false)
    }
    """
    # Verificar que OpenAI API Key esté configurada
    import os
    if not os.getenv("OPENAI_API_KEY"):
        return jsonify({
            "error": "OPENAI_API_KEY no configurada",
            "message": "Debes configurar la variable de entorno OPENAI_API_KEY en Render para generar historias con IA.",
            "instructions": "Ve a Render Dashboard → Tu servicio → Environment → Add: OPENAI_API_KEY"
        }), 500
    
    try:
        data = request.get_json() or {}
        
        count = data.get('count', 8)
        target_week = data.get('target_week')
        themes = data.get('themes')
        content_types = data.get('content_types', ['image', 'video'])
        force_regenerate = data.get('force_regenerate', False)
        
        # Determinar semana objetivo (próximo lunes)
        if not target_week:
            today = datetime.now().date()
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7  # Si hoy es lunes, siguiente lunes
            target_week = today + timedelta(days=days_until_monday)
        else:
            target_week = datetime.strptime(target_week, '%Y-%m-%d').date()
        
        # Verificar si ya hay historias para esa semana
        existing = StoryGeneration.query.filter_by(target_week=target_week).count()
        
        if existing > 0 and not force_regenerate:
            return jsonify({
                "message": f"Ya existen {existing} historias para la semana del {target_week}. Usa force_regenerate=true para regenerar.",
                "target_week": target_week.isoformat(),
                "existing_count": existing
            }), 200
        
        print(f"\n🎨 GENERANDO BATCH DE HISTORIAS")
        print(f"   Semana objetivo: {target_week}")
        print(f"   Cantidad: {count}")
        print(f"   Temas: {themes or 'Aleatorios'}")
        
        # Obtener generadores
        content_gen, image_gen, video_gen, _ = get_generators()
        
        # 1. Generar contenido con IA
        print(f"\n📝 Paso 1/3: Generando contenido...")
        story_contents = content_gen.generate_batch_content(count=count, themes=themes)
        
        if len(story_contents) < count:
            print(f"⚠️  Solo se generaron {len(story_contents)} de {count} contenidos solicitados")
        
        # 2. Generar imágenes y/o videos
        print(f"\n🎨 Paso 2/3: Generando medios...")
        batch_id = str(uuid.uuid4())
        generated_stories = []
        
        for i, content in enumerate(story_contents, 1):
            try:
                # Decidir tipo de contenido (imagen o video)
                content_type = content_types[i % len(content_types)]
                
                # Obtener URL de producto si aplica
                product_image_url = None
                if content.product:
                    product_image_url = content.product.quality_photo_url
                
                # Elegir variante de layout aleatoria (A, B, C)
                import random
                layout = random.choice(['A', 'B', 'C'])
                
                # Parsear content_data
                content_data_dict = json.loads(content.content_data)
                
                print(f"\n   [{i}/{len(story_contents)}] Generando {content.theme} ({content_type}, layout {layout})...")
                
                # Generar imagen
                image_path = image_gen.generate_story_image(
                    theme=content.theme,
                    content_data=content_data_dict,
                    product_image_url=product_image_url,
                    layout_variant=layout
                )
                
                media_url = f"/api/social/stories/media/{os.path.basename(image_path)}"
                thumbnail_url = media_url
                
                # Si es video, generar video a partir de la imagen
                if content_type == 'video':
                    try:
                        print(f"       🎬 Generando video...")
                        video_path = video_gen.generate_video_from_story(
                            theme=content.theme,
                            image_path=image_path
                        )
                        media_url = f"/api/social/stories/media/{os.path.basename(video_path)}"
                        
                        # Crear thumbnail del video
                        thumb_path = video_gen.create_thumbnail(video_path)
                        if thumb_path:
                            thumbnail_url = f"/api/social/stories/media/{os.path.basename(thumb_path)}"
                        
                        print(f"       ✅ Video generado")
                    except Exception as e:
                        print(f"       ⚠️  Error generando video, usando imagen: {str(e)}")
                        content_type = 'image'  # Fallback a imagen
                
                # Crear registro de generación
                # Obtener o crear template dummy (en el futuro será dinámico)
                template = StoryTemplate.query.filter_by(
                    theme=content.theme,
                    content_type=content_type,
                    is_active=True
                ).first()
                
                if not template:
                    # Crear template dummy
                    template = StoryTemplate(
                        name=f"Template {content.theme} {layout}",
                        theme=content.theme,
                        content_type=content_type,
                        design_config=json.dumps({"layout": layout}),
                        is_active=True
                    )
                    db.session.add(template)
                    db.session.flush()
                
                story_gen = StoryGeneration(
                    template_id=template.id,
                    content_id=content.id,
                    content_type=content_type,
                    theme=content.theme,
                    media_url=media_url,
                    thumbnail_url=thumbnail_url,
                    status='pending_review',
                    target_week=target_week,
                    batch_id=batch_id,
                    generation_metadata=json.dumps({
                        "layout": layout,
                        "generated_at": datetime.utcnow().isoformat()
                    })
                )
                
                db.session.add(story_gen)
                generated_stories.append(story_gen)
                
                print(f"       ✅ Historia generada")
                
            except Exception as e:
                print(f"       ❌ Error: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # 3. Guardar en base de datos
        print(f"\n💾 Paso 3/3: Guardando en base de datos...")
        db.session.commit()
        
        print(f"\n✅ BATCH COMPLETADO")
        print(f"   Historias generadas: {len(generated_stories)}")
        print(f"   Batch ID: {batch_id}")
        
        return jsonify({
            "message": "Historias generadas exitosamente",
            "batch_id": batch_id,
            "target_week": target_week.isoformat(),
            "generated_count": len(generated_stories),
            "stories": [story.to_dict() for story in generated_stories]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error generando batch: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@stories_bp.route('/list', methods=['GET'])
def list_stories():
    """
    Lista historias generadas con filtros
    
    Query params:
    - target_week: Filtrar por semana (formato YYYY-MM-DD)
    - status: Filtrar por estado (pending_review, approved, rejected, scheduled, published)
    - theme: Filtrar por tema
    - batch_id: Filtrar por batch
    - limit: Cantidad máxima de resultados (default: 50)
    """
    try:
        target_week = request.args.get('target_week')
        status = request.args.get('status')
        theme = request.args.get('theme')
        batch_id = request.args.get('batch_id')
        limit = request.args.get('limit', 50, type=int)
        
        query = StoryGeneration.query
        
        if target_week:
            target_week_date = datetime.strptime(target_week, '%Y-%m-%d').date()
            query = query.filter_by(target_week=target_week_date)
        
        if status:
            query = query.filter_by(status=status)
        
        if theme:
            query = query.filter_by(theme=theme)
        
        if batch_id:
            query = query.filter_by(batch_id=batch_id)
        
        stories = query.order_by(StoryGeneration.created_at.desc()).limit(limit).all()
        
        # Estadísticas
        total = query.count()
        approved = query.filter_by(status='approved').count()
        pending = query.filter_by(status='pending_review').count()
        
        return jsonify({
            "stories": [story.to_dict() for story in stories],
            "total": total,
            "stats": {
                "approved": approved,
                "pending": pending,
                "rejected": query.filter_by(status='rejected').count(),
                "scheduled": query.filter_by(status='scheduled').count(),
                "published": query.filter_by(status='published').count()
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@stories_bp.route('/<int:story_id>', methods=['GET'])
def get_story(story_id):
    """Obtiene una historia específica"""
    try:
        story = StoryGeneration.query.get_or_404(story_id)
        return jsonify(story.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@stories_bp.route('/<int:story_id>/approve', methods=['POST'])
def approve_story(story_id):
    """
    Aprueba una historia
    
    Body (opcional):
    {
        "scheduled_date": "2025-11-11T10:00:00"  # Fecha/hora de publicación
    }
    """
    try:
        story = StoryGeneration.query.get_or_404(story_id)
        
        if story.status == 'approved':
            return jsonify({"message": "Historia ya está aprobada"}), 200
        
        data = request.get_json() or {}
        scheduled_date = data.get('scheduled_date')
        
        story.status = 'approved'
        
        if scheduled_date:
            story.scheduled_date = datetime.fromisoformat(scheduled_date)
            story.status = 'scheduled'
        
        # Actualizar contador de uso del contenido
        story.content.times_used += 1
        story.content.last_used_date = datetime.utcnow()
        story.content.status = 'used'
        
        db.session.commit()
        
        print(f"✅ Historia #{story_id} aprobada")
        
        return jsonify({
            "message": "Historia aprobada",
            "story": story.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@stories_bp.route('/<int:story_id>/reject', methods=['POST'])
def reject_story(story_id):
    """
    Rechaza una historia
    
    Body (opcional):
    {
        "reason": "Motivo del rechazo"
    }
    """
    try:
        story = StoryGeneration.query.get_or_404(story_id)
        
        data = request.get_json() or {}
        reason = data.get('reason', 'No especificado')
        
        story.status = 'rejected'
        story.rejection_reason = reason
        
        db.session.commit()
        
        print(f"❌ Historia #{story_id} rechazada: {reason}")
        
        return jsonify({
            "message": "Historia rechazada",
            "story": story.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@stories_bp.route('/<int:story_id>', methods=['PATCH'])
def update_story(story_id):
    """
    Actualiza el contenido de una historia
    
    Body:
    {
        "content_data": {...}  # Nuevo contenido (sobrescribe el anterior)
    }
    """
    try:
        story = StoryGeneration.query.get_or_404(story_id)
        
        data = request.get_json()
        if not data or 'content_data' not in data:
            return jsonify({"error": "content_data es requerido"}), 400
        
        # Actualizar el contenido
        story.content.content_data = json.dumps(data['content_data'], ensure_ascii=False)
        
        # Regenerar la imagen/video con el nuevo contenido
        try:
            content_data_dict = data['content_data']
            product_image_url = None
            if story.content.product:
                product_image_url = story.content.product.quality_photo_url
            
            # Obtener layout del metadata
            metadata = json.loads(story.generation_metadata) if story.generation_metadata else {}
            layout = metadata.get('layout', 'A')
            
            # Regenerar imagen
            image_path = image_gen.generate_story_image(
                theme=story.theme,
                content_data=content_data_dict,
                product_image_url=product_image_url,
                layout_variant=layout
            )
            
            story.media_url = f"/api/social/stories/media/{os.path.basename(image_path)}"
            story.thumbnail_url = story.media_url
            
            # Si era video, regenerar video
            if story.content_type == 'video':
                video_path = video_gen.generate_video_from_story(
                    theme=story.theme,
                    image_path=image_path
                )
                story.media_url = f"/api/social/stories/media/{os.path.basename(video_path)}"
            
            print(f"✏️  Historia #{story_id} actualizada y regenerada")
            
        except Exception as e:
            print(f"⚠️  Error regenerando media: {str(e)}")
            # Continuar de todos modos con el contenido actualizado
        
        db.session.commit()
        
        return jsonify({
            "message": "Historia actualizada",
            "story": story.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@stories_bp.route('/regenerate', methods=['POST'])
def regenerate_stories():
    """
    Regenera historias adicionales para una semana que no tiene suficientes aprobadas
    
    Body:
    {
        "target_week": "2025-11-11",
        "additional_count": 3  # Cantidad adicional a generar
    }
    """
    try:
        data = request.get_json()
        if not data or 'target_week' not in data:
            return jsonify({"error": "target_week es requerido"}), 400
        
        target_week = datetime.strptime(data['target_week'], '%Y-%m-%d').date()
        additional_count = data.get('additional_count', 3)
        
        # Verificar cuántas aprobadas hay
        approved_count = StoryGeneration.query.filter_by(
            target_week=target_week,
            status='approved'
        ).count()
        
        print(f"\n🔄 REGENERANDO HISTORIAS")
        print(f"   Semana: {target_week}")
        print(f"   Aprobadas actuales: {approved_count}")
        print(f"   Adicionales a generar: {additional_count}")
        
        # Generar nuevas historias
        response = generate_batch.__wrapped__()  # Llamar a la función directamente
        
        return response
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@stories_bp.route('/media/<filename>', methods=['GET'])
def serve_media(filename):
    """Sirve archivos de media generados"""
    try:
        media_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'generated_images',
            'stories'
        )
        
        file_path = os.path.join(media_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "Archivo no encontrado"}), 404
        
        return send_file(file_path, mimetype='image/png' if filename.endswith('.png') else 'video/mp4')
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@stories_bp.route('/download/<filename>', methods=['GET'])
def download_media(filename):
    """Descarga archivos de media"""
    try:
        media_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'generated_images',
            'stories'
        )
        
        file_path = os.path.join(media_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "Archivo no encontrado"}), 404
        
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== GESTIÓN DE PLANTILLAS ==========

@stories_bp.route('/templates', methods=['GET'])
def list_templates():
    """Lista todas las plantillas de historias"""
    try:
        theme = request.args.get('theme')
        content_type = request.args.get('content_type')
        is_active = request.args.get('is_active', 'true').lower() == 'true'
        
        query = StoryTemplate.query
        
        if theme:
            query = query.filter_by(theme=theme)
        
        if content_type:
            query = query.filter_by(content_type=content_type)
        
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        
        templates = query.order_by(StoryTemplate.usage_count.desc()).all()
        
        return jsonify({
            "templates": [template.to_dict() for template in templates],
            "total": len(templates)
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@stories_bp.route('/templates/<int:template_id>', methods=['GET'])
def get_template(template_id):
    """Obtiene una plantilla específica"""
    try:
        template = StoryTemplate.query.get_or_404(template_id)
        return jsonify(template.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 404


@stories_bp.route('/templates', methods=['POST'])
def create_template():
    """
    Crea una nueva plantilla
    
    Body:
    {
        "name": "Template Tip Moderno",
        "theme": "tip_semana",
        "content_type": "image",
        "template_url": "https://...",
        "design_config": {...},
        "video_config": {...}  # solo si content_type='video'
    }
    """
    try:
        data = request.get_json()
        
        required_fields = ['name', 'theme', 'content_type']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"{field} es requerido"}), 400
        
        template = StoryTemplate(
            name=data['name'],
            theme=data['theme'],
            content_type=data['content_type'],
            template_url=data.get('template_url'),
            design_config=json.dumps(data.get('design_config', {})),
            video_config=json.dumps(data.get('video_config', {})) if data['content_type'] == 'video' else None,
            is_active=data.get('is_active', True)
        )
        
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            "message": "Plantilla creada",
            "template": template.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@stories_bp.route('/templates/<int:template_id>', methods=['PATCH'])
def update_template(template_id):
    """Actualiza una plantilla"""
    try:
        template = StoryTemplate.query.get_or_404(template_id)
        data = request.get_json()
        
        if 'name' in data:
            template.name = data['name']
        if 'template_url' in data:
            template.template_url = data['template_url']
        if 'design_config' in data:
            template.design_config = json.dumps(data['design_config'])
        if 'video_config' in data:
            template.video_config = json.dumps(data['video_config'])
        if 'is_active' in data:
            template.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            "message": "Plantilla actualizada",
            "template": template.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@stories_bp.route('/templates/<int:template_id>', methods=['DELETE'])
def delete_template(template_id):
    """Desactiva una plantilla (soft delete)"""
    try:
        template = StoryTemplate.query.get_or_404(template_id)
        template.is_active = False
        
        db.session.commit()
        
        return jsonify({"message": "Plantilla desactivada"}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ========== ESTADÍSTICAS ==========

@stories_bp.route('/stats', methods=['GET'])
def get_stats():
    """Obtiene estadísticas generales de historias"""
    try:
        target_week = request.args.get('target_week')
        
        query = StoryGeneration.query
        
        if target_week:
            target_week_date = datetime.strptime(target_week, '%Y-%m-%d').date()
            query = query.filter_by(target_week=target_week_date)
        
        stats = {
            "total": query.count(),
            "by_status": {
                "pending_review": query.filter_by(status='pending_review').count(),
                "approved": query.filter_by(status='approved').count(),
                "rejected": query.filter_by(status='rejected').count(),
                "scheduled": query.filter_by(status='scheduled').count(),
                "published": query.filter_by(status='published').count()
            },
            "by_theme": {},
            "by_content_type": {
                "image": query.filter_by(content_type='image').count(),
                "video": query.filter_by(content_type='video').count()
            }
        }
        
        # Contar por tema
        themes = ['tip_semana', 'doggo_prueba', 'mito_realidad', 'beneficio_dia', 
                  'sabias_que', 'detras_camaras', 'cliente_semana', 'desafio_receta']
        for theme in themes:
            stats['by_theme'][theme] = query.filter_by(theme=theme).count()
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== SCHEDULER ==========

@stories_bp.route('/scheduler/run', methods=['POST'])
def run_scheduler_manual():
    """
    Ejecuta el scheduler manualmente
    
    Body (opcional):
    {
        "force": true,  # Fuerza generación aunque no sea necesaria
        "count": 8,     # Cantidad a generar
        "target_week": "2025-11-11"  # Semana específica (opcional)
    }
    """
    try:
        # Obtener scheduler
        _, _, _, scheduler = get_generators()
        
        data = request.get_json() or {}
        force = data.get('force', False)
        count = data.get('count')
        target_week_str = data.get('target_week')
        
        if target_week_str:
            # Generar para una semana específica
            from datetime import datetime
            target_week = datetime.strptime(target_week_str, '%Y-%m-%d').date()
            result = scheduler.generate_batch_for_week(
                target_week=target_week,
                count=count,
                force=force
            )
            
            return jsonify({
                "ran": True,
                "target_week": target_week.isoformat(),
                "result": result
            }), 200
        else:
            # Usar lógica automática del scheduler
            result = scheduler.run_scheduled_generation()
            return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@stories_bp.route('/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """
    Obtiene el estado del scheduler
    
    Query params:
    - target_week: Semana a consultar (opcional)
    """
    try:
        # Obtener scheduler
        _, _, _, scheduler = get_generators()
        
        target_week_str = request.args.get('target_week')
        
        if target_week_str:
            from datetime import datetime
            target_week = datetime.strptime(target_week_str, '%Y-%m-%d').date()
        else:
            target_week = scheduler.get_target_week()
        
        status = scheduler.check_week_status(target_week)
        should_run = scheduler.should_run_today()
        
        return jsonify({
            "target_week": target_week.isoformat(),
            "status": status,
            "should_run_today": should_run,
            "scheduler_config": {
                "min_approved_required": scheduler.min_approved_required,
                "default_generation_count": scheduler.default_generation_count,
                "generation_days": ["Lunes", "Martes", "Miércoles"]
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

