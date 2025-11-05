"""
Modelo para instancias generadas de historias de Instagram
Una StoryGeneration combina un StoryTemplate + StoryContent + el resultado generado
"""
from datetime import datetime
import json
from ...db import db


class StoryGeneration(db.Model):
    __tablename__ = "story_generations"

    id = db.Column(db.Integer, primary_key=True)
    
    # Relaciones
    template_id = db.Column(db.Integer, db.ForeignKey('story_templates.id'), nullable=False)
    template = db.relationship('StoryTemplate', backref='generations')
    
    content_id = db.Column(db.Integer, db.ForeignKey('story_contents.id'), nullable=False)
    content = db.relationship('StoryContent', backref='generations')
    
    # Tipo y tema
    content_type = db.Column(db.String(20), nullable=False)  # 'image' o 'video'
    theme = db.Column(db.String(50), nullable=False)  # 'tip_semana', 'doggo_prueba', etc.
    
    # URLs de los archivos generados
    media_url = db.Column(db.Text, nullable=True)  # URL de la imagen o video generado
    thumbnail_url = db.Column(db.Text, nullable=True)  # Miniatura para preview
    
    # Estado del flujo de aprobación
    status = db.Column(db.String(20), nullable=False, default='pending_review')
    # 'pending_review' -> generado, esperando revisión
    # 'approved' -> aprobado por el usuario
    # 'rejected' -> rechazado
    # 'scheduled' -> programado para publicar
    # 'published' -> ya publicado
    
    rejection_reason = db.Column(db.Text, nullable=True)
    
    # Programación
    target_week = db.Column(db.Date, nullable=False)  # Lunes de la semana objetivo
    scheduled_date = db.Column(db.DateTime, nullable=True)  # Fecha/hora específica de publicación
    published_date = db.Column(db.DateTime, nullable=True)
    
    # Batch de generación (todas las generadas juntas tienen el mismo batch_id)
    batch_id = db.Column(db.String(50), nullable=False)  # UUID del batch
    
    # Metadata
    generation_metadata = db.Column(db.Text, nullable=True)  # JSON con info adicional
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        template_data = self.template.to_dict() if self.template else None
        content_data = self.content.to_dict() if self.content else None
        generation_metadata = json.loads(self.generation_metadata) if self.generation_metadata else {}
        
        return {
            "id": self.id,
            "template_id": self.template_id,
            "template": template_data,
            "content_id": self.content_id,
            "content": content_data,
            "content_type": self.content_type,
            "theme": self.theme,
            "media_url": self.media_url,
            "thumbnail_url": self.thumbnail_url,
            "status": self.status,
            "rejection_reason": self.rejection_reason,
            "target_week": self.target_week.isoformat() if self.target_week else None,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "batch_id": self.batch_id,
            "generation_metadata": generation_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

