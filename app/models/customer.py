from datetime import datetime

from ..db import db


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    phone = db.Column(db.String(40), nullable=True)
    rut = db.Column(db.String(40), nullable=True)
    nickname = db.Column(db.String(80), nullable=True)
    preferences = db.Column(db.Text, nullable=True)
    personality = db.Column(db.Text, nullable=True)
    address = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "rut": self.rut,
            "nickname": self.nickname,
            "preferences": self.preferences,
            "personality": self.personality,
            "address": self.address,
            "email": self.email,
        }
