from datetime import datetime

from ...db import db


class WhatsAppMessage(db.Model):
    __tablename__ = "whatsapp_messages"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    message_type = db.Column(
        db.String(30), 
        nullable=False
    )  # 'catalog_offer', 'reminder', 'custom'
    
    status = db.Column(
        db.String(20), 
        nullable=False, 
        default='draft'
    )  # 'draft', 'pending_approval', 'approved', 'scheduled', 'sent', 'failed'
    
    message_text = db.Column(db.Text, nullable=True)
    catalog_url = db.Column(db.Text, nullable=True)  # URL del PDF del catálogo
    
    scheduled_date = db.Column(db.DateTime, nullable=True)
    sent_date = db.Column(db.DateTime, nullable=True)
    whatsapp_message_id = db.Column(db.String(100), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relación con cliente
    customer = db.relationship('Customer', backref='whatsapp_messages')

    def to_dict(self) -> dict:
        customer_data = self.customer.to_dict() if self.customer else None
        
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "customer": customer_data,
            "message_type": self.message_type,
            "status": self.status,
            "message_text": self.message_text,
            "catalog_url": self.catalog_url,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "sent_date": self.sent_date.isoformat() if self.sent_date else None,
            "whatsapp_message_id": self.whatsapp_message_id,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

