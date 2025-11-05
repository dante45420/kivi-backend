"""
Scheduler automático para generación de historias de Instagram
Corre lunes-miércoles para generar contenido de la semana siguiente
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
import random

from ...db import db
from ..models import StoryGeneration
from .story_content_generator import StoryContentGenerator
from .story_image_generator import StoryImageGenerator
from .story_video_generator import StoryVideoGenerator


class StoryScheduler:
    """
    Scheduler para generación automática de historias
    
    Flujo:
    1. Detecta si es lunes-miércoles
    2. Calcula la fecha del próximo lunes (semana siguiente)
    3. Verifica si ya hay historias para esa semana
    4. Si no hay suficientes aprobadas (< 3), genera más
    5. Genera un batch de 6-8 historias
    """
    
    def __init__(self):
        self.content_gen = StoryContentGenerator()
        self.image_gen = StoryImageGenerator()
        self.video_gen = StoryVideoGenerator()
        
        # Configuración
        self.min_approved_required = 3
        self.default_generation_count = 8
        self.generation_days = [0, 1, 2]  # Lunes=0, Martes=1, Miércoles=2
    
    def should_run_today(self) -> bool:
        """Verifica si el scheduler debe correr hoy"""
        today = datetime.now()
        return today.weekday() in self.generation_days
    
    def get_target_week(self) -> datetime.date:
        """Calcula el lunes de la semana siguiente"""
        today = datetime.now().date()
        days_until_next_monday = (7 - today.weekday()) % 7
        if days_until_next_monday == 0:
            days_until_next_monday = 7  # Si hoy es lunes, siguiente lunes
        
        next_monday = today + timedelta(days=days_until_next_monday)
        return next_monday
    
    def check_week_status(self, target_week: datetime.date) -> Dict:
        """
        Verifica el estado de las historias para una semana específica
        
        Returns:
            {
                "total": int,
                "approved": int,
                "pending": int,
                "needs_generation": bool,
                "message": str
            }
        """
        total = StoryGeneration.query.filter_by(target_week=target_week).count()
        approved = StoryGeneration.query.filter_by(
            target_week=target_week,
            status='approved'
        ).count()
        pending = StoryGeneration.query.filter_by(
            target_week=target_week,
            status='pending_review'
        ).count()
        
        needs_generation = approved < self.min_approved_required and total < 20
        
        return {
            "total": total,
            "approved": approved,
            "pending": pending,
            "needs_generation": needs_generation,
            "message": f"Semana {target_week}: {approved} aprobadas, {pending} pendientes, {total} total"
        }
    
    def generate_batch_for_week(
        self,
        target_week: datetime.date,
        count: int = None,
        force: bool = False
    ) -> Dict:
        """
        Genera un batch de historias para una semana específica
        
        Args:
            target_week: Fecha del lunes de la semana objetivo
            count: Cantidad a generar (default: self.default_generation_count)
            force: Generar aunque ya existan suficientes
        
        Returns:
            {
                "success": bool,
                "generated_count": int,
                "batch_id": str,
                "message": str
            }
        """
        if count is None:
            count = self.default_generation_count
        
        # Verificar si es necesario generar
        status = self.check_week_status(target_week)
        
        if not force and not status['needs_generation']:
            return {
                "success": False,
                "generated_count": 0,
                "batch_id": None,
                "message": f"Ya hay {status['approved']} historias aprobadas. No es necesario generar más."
            }
        
        print(f"\n🎨 SCHEDULER: Generando historias para semana {target_week}")
        print(f"   Estado actual: {status['message']}")
        print(f"   Generando: {count} historias")
        
        try:
            # 1. Generar contenido
            story_contents = self.content_gen.generate_batch_content(count=count)
            
            if not story_contents:
                return {
                    "success": False,
                    "generated_count": 0,
                    "batch_id": None,
                    "message": "No se pudo generar contenido"
                }
            
            # 2. Generar imágenes/videos
            import uuid
            batch_id = str(uuid.uuid4())
            generated_count = 0
            
            # Mezclar tipos de contenido
            content_types = ['image', 'video', 'image', 'video', 'image', 'image', 'video', 'image']
            random.shuffle(content_types)
            
            for i, content in enumerate(story_contents):
                try:
                    content_type = content_types[i % len(content_types)]
                    layout = random.choice(['A', 'B', 'C'])
                    
                    # Obtener datos del contenido
                    content_data_dict = json.loads(content.content_data)
                    product_image_url = None
                    if content.product:
                        product_image_url = content.product.quality_photo_url
                    
                    # Generar imagen
                    image_path = self.image_gen.generate_story_image(
                        theme=content.theme,
                        content_data=content_data_dict,
                        product_image_url=product_image_url,
                        layout_variant=layout
                    )
                    
                    media_url = f"/api/social/stories/media/{os.path.basename(image_path)}"
                    thumbnail_url = media_url
                    
                    # Si es video, generar video
                    if content_type == 'video':
                        try:
                            video_path = self.video_gen.generate_video_from_story(
                                theme=content.theme,
                                image_path=image_path
                            )
                            media_url = f"/api/social/stories/media/{os.path.basename(video_path)}"
                            
                            thumb_path = self.video_gen.create_thumbnail(video_path)
                            if thumb_path:
                                thumbnail_url = f"/api/social/stories/media/{os.path.basename(thumb_path)}"
                        except Exception as e:
                            print(f"⚠️  Error generando video: {e}. Usando imagen.")
                            content_type = 'image'
                    
                    # Crear registro
                    from ..models import StoryTemplate
                    
                    template = StoryTemplate.query.filter_by(
                        theme=content.theme,
                        content_type=content_type,
                        is_active=True
                    ).first()
                    
                    if not template:
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
                            "generated_by": "scheduler",
                            "generated_at": datetime.utcnow().isoformat()
                        })
                    )
                    
                    db.session.add(story_gen)
                    generated_count += 1
                    
                except Exception as e:
                    print(f"❌ Error generando historia #{i+1}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Guardar
            db.session.commit()
            
            print(f"✅ SCHEDULER: {generated_count} historias generadas exitosamente")
            
            return {
                "success": True,
                "generated_count": generated_count,
                "batch_id": batch_id,
                "message": f"Generadas {generated_count} historias para la semana {target_week}"
            }
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ SCHEDULER: Error: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "generated_count": 0,
                "batch_id": None,
                "message": f"Error: {str(e)}"
            }
    
    def run_scheduled_generation(self) -> Dict:
        """
        Ejecuta la generación programada
        Este es el método principal que se debe llamar desde un cron job
        
        Returns:
            {
                "ran": bool,
                "reason": str,
                "target_week": str,
                "result": Dict (si corrió)
            }
        """
        # Verificar si debe correr hoy
        if not self.should_run_today():
            day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            today_name = day_names[datetime.now().weekday()]
            return {
                "ran": False,
                "reason": f"Hoy es {today_name}. El scheduler solo corre Lunes-Miércoles.",
                "target_week": None,
                "result": None
            }
        
        # Obtener semana objetivo
        target_week = self.get_target_week()
        
        # Verificar estado
        status = self.check_week_status(target_week)
        
        print(f"\n🤖 SCHEDULER AUTOMÁTICO")
        print(f"   Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"   {status['message']}")
        
        if not status['needs_generation']:
            return {
                "ran": False,
                "reason": f"Ya hay suficientes historias aprobadas ({status['approved']}/{self.min_approved_required})",
                "target_week": target_week.isoformat(),
                "result": None
            }
        
        # Generar
        result = self.generate_batch_for_week(target_week)
        
        return {
            "ran": True,
            "reason": "Generación necesaria",
            "target_week": target_week.isoformat(),
            "result": result
        }


# Función de utilidad para llamar desde cron o comando CLI
def run_scheduler():
    """Ejecuta el scheduler y devuelve resultado"""
    scheduler = StoryScheduler()
    return scheduler.run_scheduled_generation()


if __name__ == "__main__":
    # Permite ejecutar el scheduler manualmente
    print("🚀 Ejecutando Story Scheduler...")
    result = run_scheduler()
    print("\n📊 Resultado:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

