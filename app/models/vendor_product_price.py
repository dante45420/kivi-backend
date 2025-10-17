from ..db import db
from datetime import datetime


class VendorProductPrice(db.Model):
    """Precio de producto por proveedor (para comerciantes)"""
    __tablename__ = "vendor_product_prices"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id"))
    price_per_kg = db.Column(db.Float)
    price_per_unit = db.Column(db.Float)
    unit = db.Column(db.String(20), nullable=False)
    markup_percentage = db.Column(db.Float, default=20.0)
    final_price = db.Column(db.Float, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    source = db.Column(db.String(50), default='auto')  # 'auto' o 'manual'

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "vendor_id": self.vendor_id,
            "product_id": self.product_id,
            "variant_id": self.variant_id,
            "price_per_kg": self.price_per_kg,
            "price_per_unit": self.price_per_unit,
            "unit": self.unit,
            "markup_percentage": self.markup_percentage,
            "final_price": self.final_price,
            "is_available": self.is_available,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "source": self.source,
        }

