from datetime import datetime

from ..db import db


class ProductVariant(db.Model):
    __tablename__ = "product_variants"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    label = db.Column(db.String(80), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "label": self.label,
            "active": self.active,
        }


class VariantPriceTier(db.Model):
    __tablename__ = "variant_price_tiers"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id"), nullable=True)
    min_qty = db.Column(db.Float, nullable=False, default=1.0)
    unit = db.Column(db.String(16), nullable=False, default="kg")
    sale_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "variant_id": self.variant_id,
            "min_qty": self.min_qty,
            "unit": self.unit,
            "sale_price": self.sale_price,
        }



