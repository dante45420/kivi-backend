from datetime import datetime

from ..db import db


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    title = db.Column(db.String(160), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="draft")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "notes": self.notes,
            "title": self.title,
            "status": self.status,
        }
