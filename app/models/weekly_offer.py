from datetime import datetime
from ..db import db


class WeeklyOffer(db.Model):
    __tablename__ = "weekly_offers"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # 'fruta', 'verdura', 'especial'
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    price = db.Column(db.String(100), nullable=True)  # Ej: "$550 c/u", "$1.500 kg"
    reference_price = db.Column(db.String(200), nullable=True)  # Ej: "Lider $790 c/u"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación con producto
    product = db.relationship('Product', backref='weekly_offers')

    def to_dict(self) -> dict:
        product_data = self.product.to_dict() if self.product else None
        return {
            "id": self.id,
            "type": self.type,
            "product_id": self.product_id,
            "product": product_data,
            "price": self.price,
            "reference_price": self.reference_price,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

