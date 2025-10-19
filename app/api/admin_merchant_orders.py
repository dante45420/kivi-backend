"""
API para admin gestionar pedidos de comerciantes (B2B)
"""
from flask import Blueprint, jsonify, request
from datetime import datetime

from ..db import db
from ..models.merchant_order import MerchantOrder
from ..models.merchant_order_item import MerchantOrderItem
from ..models.merchant_user import MerchantUser
from .auth import require_token


admin_merchant_orders_bp = Blueprint("admin_merchant_orders", __name__)


@admin_merchant_orders_bp.get("/admin/merchant-orders")
@require_token
def list_all_merchant_orders():
    """Listar todos los pedidos de comerciantes"""
    try:
        status_filter = request.args.get('status')
        merchant_id = request.args.get('merchant_id')
        
        query = MerchantOrder.query
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        if merchant_id:
            query = query.filter_by(merchant_user_id=int(merchant_id))
        
        orders = query.order_by(MerchantOrder.created_at.desc()).all()
        
        return jsonify([o.to_dict() for o in orders]), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_merchant_orders_bp.get("/admin/merchant-orders/<int:order_id>")
@require_token
def get_merchant_order_detail(order_id):
    """Obtener detalles de un pedido"""
    try:
        order = MerchantOrder.query.get_or_404(order_id)
        return jsonify(order.to_dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_merchant_orders_bp.patch("/admin/merchant-orders/<int:order_id>/status")
@require_token
def update_merchant_order_status(order_id):
    """Actualizar estado de un pedido"""
    try:
        order = MerchantOrder.query.get_or_404(order_id)
        data = request.get_json(silent=True) or {}
        
        new_status = data.get('status')
        if new_status not in ['pending', 'confirmed', 'completed', 'cancelled']:
            return jsonify({'error': 'Estado inválido'}), 400
        
        order.status = new_status
        order.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify(order.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_merchant_orders_bp.patch("/admin/merchant-orders/<int:order_id>/items/<int:item_id>/vendor")
@require_token
def assign_vendor_to_item(order_id, item_id):
    """Asignar proveedor a un item del pedido"""
    try:
        item = MerchantOrderItem.query.filter_by(
            id=item_id,
            merchant_order_id=order_id
        ).first_or_404()
        
        data = request.get_json(silent=True) or {}
        vendor_id = data.get('vendor_id')
        
        if not vendor_id:
            return jsonify({'error': 'vendor_id es requerido'}), 400
        
        item.assigned_vendor_id = int(vendor_id)
        
        db.session.commit()
        
        return jsonify(item.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_merchant_orders_bp.get("/admin/merchants")
@require_token
def list_merchants():
    """Listar todos los comerciantes"""
    try:
        merchants = MerchantUser.query.order_by(MerchantUser.business_name).all()
        return jsonify([m.to_dict() for m in merchants]), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_merchant_orders_bp.patch("/admin/merchants/<int:merchant_id>/toggle")
@require_token
def toggle_merchant_status(merchant_id):
    """Activar/desactivar comerciante"""
    try:
        merchant = MerchantUser.query.get_or_404(merchant_id)
        merchant.is_active = not merchant.is_active
        
        db.session.commit()
        
        return jsonify(merchant.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_merchant_orders_bp.post("/admin/merchants")
@require_token
def create_merchant():
    """Crear nuevo comerciante"""
    try:
        data = request.get_json(silent=True) or {}
        
        email = (data.get('email') or '').strip()
        password = data.get('password') or ''
        business_name = (data.get('business_name') or '').strip()
        
        if not email or not password or not business_name:
            return jsonify({'error': 'Email, contraseña y nombre de negocio son requeridos'}), 400
        
        # Verificar si el email ya existe
        existing = MerchantUser.query.filter_by(email=email).first()
        if existing:
            return jsonify({'error': 'El email ya está registrado'}), 400
        
        # Crear nuevo comerciante
        merchant = MerchantUser(
            email=email,
            business_name=business_name,
            contact_name=data.get('contact_name'),
            phone=data.get('phone'),
            address=data.get('address'),
            rut=data.get('rut'),
            is_active=data.get('is_active', True)
        )
        merchant.set_password(password)
        
        db.session.add(merchant)
        db.session.commit()
        
        result = merchant.to_dict()
        result['plain_password'] = password  # Solo para respuesta de creación
        
        return jsonify(result), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_merchant_orders_bp.get("/admin/merchants/<int:merchant_id>")
@require_token
def get_merchant(merchant_id):
    """Obtener detalle de comerciante"""
    try:
        merchant = MerchantUser.query.get_or_404(merchant_id)
        return jsonify(merchant.to_dict()), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_merchant_orders_bp.patch("/admin/merchants/<int:merchant_id>")
@require_token
def update_merchant(merchant_id):
    """Actualizar comerciante"""
    try:
        merchant = MerchantUser.query.get_or_404(merchant_id)
        data = request.get_json(silent=True) or {}
        
        # Actualizar campos
        if 'email' in data:
            email = data['email'].strip()
            # Verificar que no exista otro merchant con ese email
            existing = MerchantUser.query.filter(
                MerchantUser.email == email,
                MerchantUser.id != merchant_id
            ).first()
            if existing:
                return jsonify({'error': 'El email ya está en uso'}), 400
            merchant.email = email
        
        if 'business_name' in data:
            merchant.business_name = data['business_name'].strip()
        
        if 'contact_name' in data:
            merchant.contact_name = data['contact_name']
        
        if 'phone' in data:
            merchant.phone = data['phone']
        
        if 'address' in data:
            merchant.address = data['address']
        
        if 'rut' in data:
            merchant.rut = data['rut']
        
        if 'is_active' in data:
            merchant.is_active = bool(data['is_active'])
        
        # Cambiar contraseña si se proporciona
        if 'password' in data and data['password']:
            merchant.set_password(data['password'])
        
        db.session.commit()
        
        return jsonify(merchant.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_merchant_orders_bp.delete("/admin/merchants/<int:merchant_id>")
@require_token
def delete_merchant(merchant_id):
    """Eliminar comerciante"""
    try:
        merchant = MerchantUser.query.get_or_404(merchant_id)
        db.session.delete(merchant)
        db.session.commit()
        
        return jsonify({'message': 'Comerciante eliminado'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

