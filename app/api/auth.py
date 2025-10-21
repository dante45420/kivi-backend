from functools import wraps
from flask import current_app, request, jsonify, Blueprint
from typing import Optional
import os

auth_bp = Blueprint('auth', __name__)

# Credenciales del admin (en producción usar base de datos)
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "danteparodiwerth@gmail.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Dante454@")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "kivi-admin-token-2024")


def _get_token_from_request() -> Optional[str]:
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return request.headers.get("X-API-Token")


def require_token(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _get_token_from_request()
        if not token or token != ADMIN_TOKEN:
            response = jsonify({"error": "unauthorized"})
            response.status_code = 401
            # Agregar headers CORS manualmente para errores de autenticación
            response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
            response.headers['Access-Control-Allow-Credentials'] = 'false'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Token, X-API-Token'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            return response
        return fn(*args, **kwargs)

    return wrapper


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        return jsonify({
            "success": True,
            "token": ADMIN_TOKEN,
            "user": {
                "email": ADMIN_EMAIL,
                "name": "Admin"
            }
        })
    
    return jsonify({"error": "Credenciales incorrectas"}), 401


@auth_bp.route('/verify', methods=['GET'])
@require_token
def verify():
    return jsonify({
        "success": True,
        "user": {
            "email": ADMIN_EMAIL,
            "name": "Admin"
        }
    })
