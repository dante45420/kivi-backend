"""
Modelo para plantillas de historias de Instagram
Permite subir y gestionar diferentes diseños
"""
from datetime import datetime
import json
from ...db import db


class StoryTemplate(db.Model):
    __tablename__ = "story_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # "Template Tip Moderno", "Template Doggo Divertido"
    theme = db.Column(db.String(50), nullable=False)  # 'tip_semana', 'doggo_prueba', 'mito_realidad', etc.
    
    # Tipo de contenido
    content_type = db.Column(db.String(20), nullable=False)  # 'image' o 'video'
    
    # URL de la plantilla base (imagen PNG)
    template_url = db.Column(db.Text, nullable=True)  # URL de la plantilla (puede ser Cloudinary)
    
    # Configuración de diseño en JSON
    design_config = db.Column(db.Text, nullable=True)  # JSON con posiciones, colores, fuentes
    # Ejemplo: {
    #   "text_areas": [
    #     {"id": "title", "x": 540, "y": 200, "width": 900, "height": 100, "font_size": 72, "align": "center"},
    #     {"id": "body", "x": 540, "y": 400, "width": 900, "height": 600, "font_size": 48, "align": "left"}
    #   ],
    #   "image_areas": [
    #     {"id": "product", "x": 540, "y": 1100, "width": 400, "height": 400}
    #   ],
    #   "colors": {
    #     "primary": "#3C794C",
    #     "secondary": "#FFD4A3",
    #     "text": "#2C2C2C"
    #   }
    # }
    
    # Configuración de video (si aplica)
    video_config = db.Column(db.Text, nullable=True)  # JSON con duración, transiciones, música
    # Ejemplo: {
    #   "duration": 15,
    #   "transitions": ["fade", "slide"],
    #   "music_url": "url_musica.mp3",
    #   "animation_style": "zoom_in"
    # }
    
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    usage_count = db.Column(db.Integer, nullable=False, default=0)  # Cuántas veces se ha usado
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        design_config = json.loads(self.design_config) if self.design_config else {}
        video_config = json.loads(self.video_config) if self.video_config else {}
        
        return {
            "id": self.id,
            "name": self.name,
            "theme": self.theme,
            "content_type": self.content_type,
            "template_url": self.template_url,
            "design_config": design_config,
            "video_config": video_config,
            "is_active": self.is_active,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

