from ..db import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class MerchantUser(db.Model):
    """Usuario comerciante (cliente B2B)"""
    __tablename__ = "merchant_users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    business_name = db.Column(db.String(200), nullable=False)
    contact_name = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    rut = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password: str):
        """Establecer contraseña hasheada"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verificar contraseña"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "business_name": self.business_name,
            "contact_name": self.contact_name,
            "phone": self.phone,
            "address": self.address,
            "rut": self.rut,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

