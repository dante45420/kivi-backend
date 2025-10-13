from functools import wraps
from flask import current_app, request, jsonify
from typing import Optional


def _get_token_from_request() -> Optional[str]:
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return request.headers.get("X-API-Token")


def require_token(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("SECRET_TOKEN")
        token = _get_token_from_request()
        if not expected or token != expected:
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)

    return wrapper
