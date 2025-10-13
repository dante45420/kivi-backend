from datetime import date, datetime

from ..db import db


class PriceHistory(db.Model):
    __tablename__ = "price_history"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    cost = db.Column(db.Float, nullable=True)
    sale = db.Column(db.Float, nullable=True)
    unit = db.Column(db.String(16), nullable=True)  # 'kg' o 'unit'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "date": self.date.isoformat(),
            "cost": self.cost,
            "sale": self.sale,
            "unit": self.unit,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
