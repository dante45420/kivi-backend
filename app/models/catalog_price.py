from datetime import date, datetime

from ..db import db


class CatalogPrice(db.Model):
    __tablename__ = "catalog_prices"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    sale_price = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(16), nullable=True)  # 'kg' o 'unit'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "date": self.date.isoformat(),
            "sale_price": self.sale_price,
            "unit": self.unit,
        }



