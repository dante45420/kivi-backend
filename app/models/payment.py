from datetime import datetime

from ..db import db


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(32), nullable=True)
    reference = db.Column(db.String(120), nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "amount": self.amount,
            "method": self.method,
            "reference": self.reference,
            "date": self.date.isoformat() if self.date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PaymentApplication(db.Model):
    __tablename__ = "payment_applications"

    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id"), nullable=False)
    charge_id = db.Column(db.Integer, db.ForeignKey("charges.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "payment_id": self.payment_id,
            "charge_id": self.charge_id,
            "amount": self.amount,
        }


