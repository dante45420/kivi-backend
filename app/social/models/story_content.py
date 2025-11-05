"""
Modelo para contenido de historias (tips, mitos, datos curiosos)
Permite generar y no repetir contenido
"""
from datetime import datetime
import json
from ...db import db


class StoryContent(db.Model):
    __tablename__ = "story_contents"

    id = db.Column(db.Integer, primary_key=True)
    theme = db.Column(db.String(50), nullable=False)  # 'tip_semana', 'mito_realidad', 'sabias_que', etc.
    
    # Contenido en JSON
    content_data = db.Column(db.Text, nullable=False)  # JSON con el contenido específico
    # Ejemplos:
    # TIP: {"title": "Cómo guardar tomates", "steps": ["Paso 1...", "Paso 2..."], "tip": "Pro tip..."}
    # MITO: {"myth": "Los tomates en nevera duran más", "reality": "Falso...", "explanation": "..."}
    # SABIAS_QUE: {"fact": "Las zanahorias eran moradas", "explanation": "..."}
    # BENEFICIO: {"product_id": 45, "benefits": ["Vitamina A", "Fibra"], "description": "..."}
    # DOGGO: {"product_id": 78, "reaction": "love", "text": "¡Me encanta!"}
    
    # Producto relacionado (si aplica)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    product = db.relationship('Product', backref='story_contents')
    
    # Estado
    status = db.Column(db.String(20), nullable=False, default='draft')  # 'draft', 'ready', 'used', 'archived'
    times_used = db.Column(db.Integer, nullable=False, default=0)
    last_used_date = db.Column(db.DateTime, nullable=True)
    
    # Generación
    generated_by = db.Column(db.String(20), nullable=False)  # 'ai', 'manual'
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        content_data = json.loads(self.content_data) if self.content_data else {}
        product_data = self.product.to_dict() if self.product else None
        
        return {
            "id": self.id,
            "theme": self.theme,
            "content_data": content_data,
            "product_id": self.product_id,
            "product": product_data,
            "status": self.status,
            "times_used": self.times_used,
            "last_used_date": self.last_used_date.isoformat() if self.last_used_date else None,
            "generated_by": self.generated_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

