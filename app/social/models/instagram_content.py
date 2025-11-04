from datetime import datetime
import json

from ...db import db


class InstagramContent(db.Model):
    __tablename__ = "instagram_content"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # 'post', 'story', 'reel', 'carousel'
    template_type = db.Column(db.String(50), nullable=True)  # 'ofertas_semana', 'tip_semana', 'doggo_prueba', etc.
    status = db.Column(
        db.String(20), 
        nullable=False, 
        default='draft'
    )  # 'draft', 'pending_approval', 'approved', 'scheduled', 'published', 'rejected'
    
    # Contenido en formato JSON
    content_data = db.Column(db.Text, nullable=True)  # JSON con texto, hashtags, menciones
    media_urls = db.Column(db.Text, nullable=True)  # JSON array con URLs de imágenes/videos
    
    scheduled_date = db.Column(db.DateTime, nullable=True)
    published_date = db.Column(db.DateTime, nullable=True)
    instagram_post_id = db.Column(db.String(100), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self) -> dict:
        content_data = json.loads(self.content_data) if self.content_data else {}
        media_urls = json.loads(self.media_urls) if self.media_urls else []
        
        return {
            "id": self.id,
            "type": self.type,
            "template_type": self.template_type,
            "status": self.status,
            "content_data": content_data,
            "media_urls": media_urls,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "published_date": self.published_date.isoformat() if self.published_date else None,
            "instagram_post_id": self.instagram_post_id,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

