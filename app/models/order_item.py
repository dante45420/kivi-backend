from ..db import db


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    qty = db.Column(db.Float, nullable=False)
    # unidad solicitada por el cliente (lo que pidió)
    unit = db.Column(db.String(16), nullable=False, default="kg")
    # unidad de cobro para el ítem (kg o unit)
    charged_unit = db.Column(db.String(16), nullable=True)
    # cantidad expresada en la unidad de cobro (si difiere de la solicitada)
    charged_qty = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    variant_id = db.Column(db.Integer, db.ForeignKey("product_variants.id"), nullable=True)
    sale_unit_price = db.Column(db.Float, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "product_id": self.product_id,
            "qty": self.qty,
            "unit": self.unit,
            "charged_unit": self.charged_unit,
            "charged_qty": self.charged_qty,
            "notes": self.notes,
            "variant_id": self.variant_id,
            "sale_unit_price": self.sale_unit_price,
        }
