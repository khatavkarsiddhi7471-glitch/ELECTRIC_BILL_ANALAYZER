"""
Authentication utilities, password hashing, and JWT authorization helpers.
"""

from functools import wraps
from flask import request, jsonify
import jwt
import bcrypt
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from backend.config import Config
from backend.utils.db import get_db

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def generate_token(user_id: str, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + Config.JWT_ACCESS_TOKEN_EXPIRES
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm="HS256")

def decode_token(token: str):
    try:
        return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({
                "success": False,
                "error": {"code": "UNAUTHORIZED", "message": "Missing or invalid authorization token"}
            }), 401
            
        token = auth_header.split(" ")[1].strip()
        payload = decode_token(token)
        if not payload:
            return jsonify({
                "success": False,
                "error": {"code": "TOKEN_EXPIRED", "message": "Session expired or token invalid. Please log in again."}
            }), 401
            
        db = get_db()
        try:
            user = db.users.find_one({"_id": ObjectId(payload["sub"])})
        except Exception:
            user = db.users.find_one({"_id": payload["sub"]})
            
        if not user:
            return jsonify({
                "success": False,
                "error": {"code": "USER_NOT_FOUND", "message": "User account no longer exists"}
            }), 401
            
        return f(current_user=user, *args, **kwargs)
    return decorated
