from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from ..db import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="vendor")  # 'admin' o 'vendor'
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Comisión del vendedor (% de la utilidad que se queda el vendedor)
    # Por defecto 50% para vendedores (el otro 50% es para admin por logística y compras)
    commission_rate = db.Column(db.Float, nullable=False, default=0.50)

    def set_password(self, password: str):
        """Genera el hash de la contraseña"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifica si la contraseña es correcta"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "active": self.active,
            "commission_rate": self.commission_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def to_dict_public(self) -> dict:
        """Versión pública sin información sensible"""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
        }

