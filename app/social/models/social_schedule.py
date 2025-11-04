from datetime import datetime

from ...db import db


class SocialSchedule(db.Model):
    __tablename__ = "social_schedule"

    id = db.Column(db.Integer, primary_key=True)
    content_type = db.Column(
        db.String(30), 
        nullable=False
    )  # 'instagram_post', 'whatsapp_batch'
    reference_id = db.Column(db.Integer, nullable=False)  # ID del contenido relacionado
    
    scheduled_date = db.Column(db.DateTime, nullable=False)
    
    status = db.Column(
        db.String(20), 
        nullable=False, 
        default='scheduled'
    )  # 'scheduled', 'processing', 'completed', 'failed'
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content_type": self.content_type,
            "reference_id": self.reference_id,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

