from datetime import datetime

from ..db import db


class InventoryLot(db.Model):
    __tablename__ = "inventory_lots"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    source_purchase_id = db.Column(db.Integer, db.ForeignKey("purchases.id"), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    qty_kg = db.Column(db.Float, nullable=True)
    qty_unit = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(24), nullable=False, default="unassigned")  # unassigned|assigned|processed|gift|waste
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "source_purchase_id": self.source_purchase_id,
            "order_id": self.order_id,
            "qty_kg": self.qty_kg,
            "qty_unit": self.qty_unit,
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ProcessingRecord(db.Model):
    __tablename__ = "processing_records"

    id = db.Column(db.Integer, primary_key=True)
    from_product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    to_product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    input_qty_kg = db.Column(db.Float, nullable=False)
    output_qty = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(16), nullable=False, default="unit")
    yield_percent = db.Column(db.Float, nullable=True)
    cost_transferred = db.Column(db.Float, nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "from_product_id": self.from_product_id,
            "to_product_id": self.to_product_id,
            "input_qty_kg": self.input_qty_kg,
            "output_qty": self.output_qty,
            "unit": self.unit,
            "yield_percent": self.yield_percent,
            "cost_transferred": self.cost_transferred,
            "date": self.date.isoformat() if self.date else None,
        }


