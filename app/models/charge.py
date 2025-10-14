from datetime import datetime

from ..db import db


class Charge(db.Model):
    __tablename__ = "charges"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    original_order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)  # pedido original (se mantiene al reasignar)
    order_item_id = db.Column(db.Integer, db.ForeignKey("order_items.id"), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    qty = db.Column(db.Float, nullable=False, default=0.0)  # cantidad pedida (original)
    charged_qty = db.Column(db.Float, nullable=True)  # cantidad a cobrar (puede diferir por conversión)
    unit = db.Column(db.String(16), nullable=False, default="kg")
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    discount_amount = db.Column(db.Float, nullable=False, default=0.0)
    discount_reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(16), nullable=False, default="pending")  # pending|paid|cancelled
    total = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "order_id": self.order_id,
            "original_order_id": self.original_order_id,
            "order_item_id": self.order_item_id,
            "product_id": self.product_id,
            "qty": self.qty,
            "charged_qty": self.charged_qty,
            "unit": self.unit,
            "unit_price": self.unit_price,
            "discount_amount": self.discount_amount,
            "discount_reason": self.discount_reason,
            "status": self.status,
            "total": self.total,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }


