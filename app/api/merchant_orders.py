"""
API de pedidos y carrito para comerciantes
"""
from flask import Blueprint, jsonify, request
from datetime import datetime

from ..db import db
from ..models.merchant_order import MerchantOrder
from ..models.merchant_order_item import MerchantOrderItem
from ..models.product import Product
from ..models.variant import ProductVariant
from ..models.vendor import Vendor


merchant_orders_bp = Blueprint("merchant_orders", __name__)


def require_merchant_token(func):
    """Decorator para validar token de comerciante"""
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        token = request.headers.get('X-API-Token') or request.headers.get('X-Merchant-Token')
        
        if not token or not token.startswith('merchant_'):
            return jsonify({'error': 'No autorizado'}), 401
        
        try:
            user_id = int(token.replace('merchant_', ''))
            from ..models.merchant_user import MerchantUser
            user = MerchantUser.query.get(user_id)
            
            if not user or not user.is_active:
                return jsonify({'error': 'No autorizado'}), 401
            
            return func(user, *args, **kwargs)
        except:
            return jsonify({'error': 'No autorizado'}), 401
    
    return wrapper


@merchant_orders_bp.post("/merchant/orders")
@require_merchant_token
def create_merchant_order(user):
    """Crear un nuevo pedido"""
    try:
        data = request.get_json(silent=True) or {}
        items_data = data.get('items', [])
        
        if not items_data:
            return jsonify({'error': 'El pedido debe tener al menos un producto'}), 400
        
        # Crear la orden
        order = MerchantOrder(
            merchant_user_id=user.id,
            order_number=f"M{user.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            status='pending',
            delivery_address=data.get('delivery_address'),
            delivery_date=datetime.strptime(data['delivery_date'], '%Y-%m-%d').date() if data.get('delivery_date') else None,
            notes=data.get('notes')
        )
        
        db.session.add(order)
        db.session.flush()  # Para obtener el ID
        
        # Agregar items
        subtotal = 0
        for item_data in items_data:
            product_id = item_data.get('product_id')
            variant_id = item_data.get('variant_id')
            qty = float(item_data.get('qty', 0))
            unit = item_data.get('unit', 'kg')
            price_per_unit = float(item_data.get('price_per_unit', 0))
            preferred_vendor_id = item_data.get('preferred_vendor_id')
            
            if not product_id or qty <= 0 or price_per_unit <= 0:
                db.session.rollback()
                return jsonify({'error': 'Datos inválidos en los items'}), 400
            
            item_subtotal = qty * price_per_unit
            
            order_item = MerchantOrderItem(
                merchant_order_id=order.id,
                product_id=product_id,
                variant_id=variant_id,
                qty=qty,
                unit=unit,
                price_per_unit=price_per_unit,
                subtotal=item_subtotal,
                preferred_vendor_id=preferred_vendor_id,
                notes=item_data.get('notes')
            )
            
            db.session.add(order_item)
            subtotal += item_subtotal
        
        # Actualizar totales
        delivery_fee = float(data.get('delivery_fee', 0))
        order.subtotal = subtotal
        order.delivery_fee = delivery_fee
        order.total_amount = subtotal + delivery_fee
        
        db.session.commit()
        
        return jsonify(order.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        print(f"Error en create_merchant_order: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@merchant_orders_bp.get("/merchant/orders")
@require_merchant_token
def list_merchant_orders(user):
    """Listar pedidos del comerciante"""
    try:
        orders = MerchantOrder.query.filter_by(
            merchant_user_id=user.id
        ).order_by(MerchantOrder.created_at.desc()).all()
        
        return jsonify([o.to_dict() for o in orders]), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@merchant_orders_bp.get("/merchant/orders/<int:order_id>")
@require_merchant_token
def get_merchant_order(user, order_id):
    """Obtener detalles de un pedido"""
    try:
        order = MerchantOrder.query.filter_by(
            id=order_id,
            merchant_user_id=user.id
        ).first_or_404()
        
        return jsonify(order.to_dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

