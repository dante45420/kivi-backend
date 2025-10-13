from datetime import datetime

from ..db import db


class Purchase(db.Model):
    __tablename__ = "purchases"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    qty_kg = db.Column(db.Float, nullable=True)
    qty_unit = db.Column(db.Float, nullable=True)
    charged_unit = db.Column(db.String(16), nullable=True)  # 'kg' o 'unit'
    # cantidades equivalentes convertidas para conciliación (opcional)
    eq_qty_kg = db.Column(db.Float, nullable=True)
    eq_qty_unit = db.Column(db.Float, nullable=True)
    price_total = db.Column(db.Float, nullable=True)
    price_per_unit = db.Column(db.Float, nullable=True)
    # nuevo: monto facturado esperado (según precios del pedido en la unidad de cobro)
    billed_expected = db.Column(db.Float, nullable=True)
    vendor = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    customers = db.Column(db.Text, nullable=True)  # csv simple de clientes incluidos para compra masiva
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "qty_kg": self.qty_kg,
            "qty_unit": self.qty_unit,
            "charged_unit": self.charged_unit,
            "eq_qty_kg": self.eq_qty_kg,
            "eq_qty_unit": self.eq_qty_unit,
            "price_total": self.price_total,
            "price_per_unit": self.price_per_unit,
            "billed_expected": self.billed_expected,
            "vendor": self.vendor,
            "notes": self.notes,
            "customers": self.customers,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
