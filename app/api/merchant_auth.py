"""
API de autenticación para comerciantes (merchant users)
"""
from flask import Blueprint, jsonify, request
from datetime import datetime

from ..db import db
from ..models.merchant_user import MerchantUser

merchant_auth_bp = Blueprint("merchant_auth", __name__)


@merchant_auth_bp.post("/merchant/auth/login")
def merchant_login():
    """Login para comerciantes"""
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip()
        password = data.get('password') or ''
        
        if not email or not password:
            return jsonify({'error': 'Email y contraseña son requeridos'}), 400
        
        # Buscar usuario
        user = MerchantUser.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({'error': 'Credenciales inválidas'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Usuario desactivado'}), 403
        
        # Verificar contraseña
        if not user.check_password(password):
            return jsonify({'error': 'Credenciales inválidas'}), 401
        
        # Actualizar último login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Retornar token (simple - solo el ID por ahora)
        # En producción deberías usar JWT
        return jsonify({
            'token': f"merchant_{user.id}",
            'user': user.to_dict()
        }), 200
    
    except Exception as e:
        print(f"Error en merchant_login: {e}")
        return jsonify({'error': str(e)}), 500


@merchant_auth_bp.get("/merchant/auth/me")
def merchant_me():
    """Obtener info del usuario actual"""
    try:
        token = request.headers.get('X-API-Token') or request.headers.get('X-Merchant-Token')
        
        if not token or not token.startswith('merchant_'):
            return jsonify({'error': 'No autorizado'}), 401
        
        user_id = int(token.replace('merchant_', ''))
        user = MerchantUser.query.get(user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'No autorizado'}), 401
        
        return jsonify(user.to_dict()), 200
    
    except Exception as e:
        print(f"Error en merchant_me: {e}")
        return jsonify({'error': str(e)}), 500

