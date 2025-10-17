from ..db import db
from datetime import datetime


class MerchantOrder(db.Model):
    """Pedido de comerciante"""
    __tablename__ = "merchant_orders"

    id = db.Column(db.Integer, primary_key=True)
    merchant_user_id = db.Column(db.Integer, db.ForeignKey("merchant_users.id"), nullable=False)
    order_number = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(50), default='pending')
    subtotal = db.Column(db.Float, default=0)
    delivery_fee = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    delivery_address = db.Column(db.Text)
    delivery_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "merchant_user_id": self.merchant_user_id,
            "order_number": self.order_number,
            "status": self.status,
            "subtotal": self.subtotal,
            "delivery_fee": self.delivery_fee,
            "total_amount": self.total_amount,
            "delivery_address": self.delivery_address,
            "delivery_date": self.delivery_date.isoformat() if self.delivery_date else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

