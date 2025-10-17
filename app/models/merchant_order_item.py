from ..db import db
from datetime import datetime


class MerchantOrderItem(db.Model):
    """Item de pedido de comerciante"""
    __tablename__ = "merchant_order_items"

    id = db.Column(db.Integer, primary_key=True)
    merchant_order_id = db.Column(db.Integer, db.ForeignKey("merchant_orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id"))
    qty = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    price_per_unit = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    preferred_vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"))
    assigned_vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "merchant_order_id": self.merchant_order_id,
            "product_id": self.product_id,
            "variant_id": self.variant_id,
            "qty": self.qty,
            "unit": self.unit,
            "price_per_unit": self.price_per_unit,
            "subtotal": self.subtotal,
            "preferred_vendor_id": self.preferred_vendor_id,
            "assigned_vendor_id": self.assigned_vendor_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

