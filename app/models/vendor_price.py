from datetime import date, datetime

from ..db import db


class VendorPrice(db.Model):
    __tablename__ = "vendor_prices"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    cost = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(16), nullable=True)  # 'kg' o 'unit'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "vendor_id": self.vendor_id,
            "date": self.date.isoformat(),
            "cost": self.cost,
            "unit": self.unit,
        }



