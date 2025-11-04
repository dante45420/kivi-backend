from datetime import datetime
import json

from ...db import db


class ContentTemplate(db.Model):
    __tablename__ = "content_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # 'tip_semana', 'doggo_prueba', etc.
    template_type = db.Column(db.String(20), nullable=False)  # 'post', 'story', 'reel', 'carousel'
    
    # Estructura del template en formato JSON
    content_structure = db.Column(db.Text, nullable=True)  # JSON con estructura del template
    default_hashtags = db.Column(db.Text, nullable=True)  # JSON array con hashtags por defecto
    color_palette = db.Column(db.Text, nullable=True)  # JSON con colores de la paleta
    
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self) -> dict:
        content_structure = json.loads(self.content_structure) if self.content_structure else {}
        default_hashtags = json.loads(self.default_hashtags) if self.default_hashtags else []
        color_palette = json.loads(self.color_palette) if self.color_palette else {}
        
        return {
            "id": self.id,
            "name": self.name,
            "template_type": self.template_type,
            "content_structure": content_structure,
            "default_hashtags": default_hashtags,
            "color_palette": color_palette,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

