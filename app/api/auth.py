from functools import wraps
from flask import current_app, request, jsonify, Blueprint
from typing import Optional
import os
import jwt
import datetime

from ..db import db
from ..models.user import User

auth_bp = Blueprint('auth', __name__)

# Secret key para JWT (en producción usar variable de entorno)
JWT_SECRET = os.getenv("JWT_SECRET", "kivi-jwt-secret-2024-very-secure-key")
JWT_ALGORITHM = "HS256"


def _get_token_from_request() -> Optional[str]:
    """Obtiene el token JWT del header Authorization"""
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return request.headers.get("X-API-Token")


def _decode_token(token: str) -> Optional[dict]:
    """Decodifica y valida un token JWT"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def _generate_token(user: User) -> str:
    """Genera un token JWT para el usuario"""
    payload = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def require_token(fn):
    """Decorator que requiere un token JWT válido"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _get_token_from_request()
        if not token:
            response = jsonify({"error": "unauthorized", "message": "Token no proporcionado"})
            response.status_code = 401
            # Agregar headers CORS manualmente para errores de autenticación
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'false'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Token, X-API-Token'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            return response
        
        # Decodificar token
        payload = _decode_token(token)
        if not payload:
            response = jsonify({"error": "unauthorized", "message": "Token inválido o expirado"})
            response.status_code = 401
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'false'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Token, X-API-Token'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            return response
        
        # Verificar que el usuario existe y está activo
        user = User.query.get(payload.get("user_id"))
        if not user or not user.active:
            response = jsonify({"error": "unauthorized", "message": "Usuario no encontrado o inactivo"})
            response.status_code = 401
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'false'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Token, X-API-Token'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            return response
        
        # Agregar información del usuario al request para acceso en el endpoint
        request.current_user = user
        
        return fn(*args, **kwargs)

    return wrapper


def require_admin(fn):
    """Decorator que requiere rol de admin"""
    @wraps(fn)
    @require_token
    def wrapper(*args, **kwargs):
        user = getattr(request, 'current_user', None)
        if not user or user.role != 'admin':
            response = jsonify({"error": "forbidden", "message": "Se requiere rol de administrador"})
            response.status_code = 403
            return response
        return fn(*args, **kwargs)
    
    return wrapper


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login con email y contraseña, retorna JWT token"""
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    if not email or not password:
        return jsonify({"error": "Email y contraseña son requeridos"}), 400
    
    # Buscar usuario por email
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({"error": "Credenciales incorrectas"}), 401
    
    # Verificar contraseña
    if not user.check_password(password):
        return jsonify({"error": "Credenciales incorrectas"}), 401
    
    # Verificar que el usuario esté activo
    if not user.active:
        return jsonify({"error": "Usuario desactivado"}), 403
    
    # Generar token
    token = _generate_token(user)
    
    return jsonify({
        "success": True,
        "token": token,
        "user": user.to_dict_public()
    })


@auth_bp.route('/verify', methods=['GET'])
@require_token
def verify():
    """Verifica que el token actual sea válido y retorna info del usuario"""
    user = getattr(request, 'current_user', None)
    if not user:
        return jsonify({"error": "unauthorized"}), 401
    
    return jsonify({
        "success": True,
        "user": user.to_dict_public()
    })
