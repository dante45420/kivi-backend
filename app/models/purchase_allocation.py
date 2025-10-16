from datetime import datetime

from ..db import db


class PurchaseAllocation(db.Model):
    __tablename__ = "purchase_allocations"

    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey("purchases.id"), nullable=False)
    order_item_id = db.Column(db.Integer, db.ForeignKey("order_items.id"), nullable=False)
    qty = db.Column(db.Float, nullable=False, default=0.0)
    unit = db.Column(db.String(16), nullable=False, default="kg")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "purchase_id": self.purchase_id,
            "order_item_id": self.order_item_id,
            "qty": self.qty,
            "unit": self.unit,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }



