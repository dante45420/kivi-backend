from datetime import datetime

from ..db import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    default_unit = db.Column(db.String(16), nullable=False, default="kg")
    notes = db.Column(db.Text, nullable=True)
    quality_notes = db.Column(db.Text, nullable=True)
    quality_photo_url = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "default_unit": self.default_unit,
            "notes": self.notes,
            "quality_notes": self.quality_notes,
            "quality_photo_url": self.quality_photo_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
