"""
Authentication and user profile endpoints.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import secrets
from backend.utils.db import get_db
from backend.utils.auth_guard import hash_password, check_password, generate_token, token_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    consumer_number = data.get("consumer_number", "").strip()
    
    if not name or not email or not password:
        return jsonify({
            "success": False,
            "error": {"code": "VALIDATION_ERROR", "message": "Name, email, and password are required"}
        }), 400
        
    if len(password) < 8:
        return jsonify({
            "success": False,
            "error": {"code": "VALIDATION_ERROR", "message": "Password must be at least 8 characters long"}
        }), 400
        
    db = get_db()
    existing = db.users.find_one({"email": email})
    if existing:
        return jsonify({
            "success": False,
            "error": {"code": "EMAIL_EXISTS", "message": "An account with this email already exists"}
        }), 400
        
    # Get default tariff ID
    default_tariff = db.tariffs.find_one({"user_id": None, "is_default": True})
    active_tariff_id = default_tariff["_id"] if default_tariff else None
    
    user_doc = {
        "name": name,
        "email": email,
        "password_hash": hash_password(password),
        "consumer_number": consumer_number,
        "active_tariff_id": active_tariff_id,
        "settings": {
            "monthly_unit_threshold": 200,
            "monthly_budget": 1500,
            "alert_increase_pct": 20
        },
        "state": data.get("state", "Maharashtra"),
        "distributor": data.get("distributor", "MSEDCL"),
        "created_at": datetime.now(timezone.utc)
    }
    
    res = db.users.insert_one(user_doc)
    user_id = str(res.inserted_id)
    token = generate_token(user_id, email)
    
    return jsonify({
        "success": True,
        "message": "User registered successfully",
        "data": {
            "token": token,
            "user": {
                "id": user_id,
                "name": name,
                "email": email,
                "consumer_number": consumer_number,
                "settings": user_doc["settings"]
            }
        }
    }), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({
            "success": False,
            "error": {"code": "VALIDATION_ERROR", "message": "Email and password are required"}
        }), 400
        
    db = get_db()
    user = db.users.find_one({"email": email})
    if not user or not check_password(password, user.get("password_hash", "")):
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"}
        }), 401
        
    user_id = str(user["_id"])
    token = generate_token(user_id, email)
    
    return jsonify({
        "success": True,
        "message": "Login successful",
        "data": {
            "token": token,
            "user": {
                "id": user_id,
                "name": user.get("name"),
                "email": user.get("email"),
                "consumer_number": user.get("consumer_number", ""),
                "settings": user.get("settings", {
                    "monthly_unit_threshold": 200,
                    "monthly_budget": 1500,
                    "alert_increase_pct": 20
                })
            }
        }
    }), 200

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """
    Initiate password reset. Generates a one-time token valid for 15 minutes.
    The token is returned in the response (in-app flow, no email server needed).
    """
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Email is required"}}), 400
    
    db = get_db()
    user = db.users.find_one({"email": email})
    if not user:
        # Return generic success to prevent email enumeration
        return jsonify({
            "success": True,
            "message": "If an account with that email exists, a reset code has been generated.",
            "data": {"token": None, "found": False}
        }), 200
    
    # Generate a 6-digit OTP and a secure token
    otp = str(secrets.randbelow(900000) + 100000)  # 6-digit OTP: 100000–999999
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    # Store reset info in the user document
    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "reset_token": reset_token,
            "reset_otp": otp,
            "reset_expires": expires_at
        }}
    )
    
    return jsonify({
        "success": True,
        "message": "Reset code generated successfully.",
        "data": {
            "reset_token": reset_token,
            "otp": otp,  # In production this would be sent via email/SMS
            "expires_in_minutes": 15,
            "user_name": user.get("name", "")
        }
    }), 200

@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """
    Reset password using the token + OTP received from /forgot-password.
    """
    data = request.get_json() or {}
    reset_token = data.get("reset_token", "").strip()
    otp = data.get("otp", "").strip()
    new_password = data.get("new_password", "")
    
    if not reset_token or not otp or not new_password:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Reset token, OTP, and new password are required"}}), 400
    
    if len(new_password) < 8:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Password must be at least 8 characters"}}), 400
    
    db = get_db()
    now = datetime.now(timezone.utc)
    
    user = db.users.find_one({"reset_token": reset_token, "reset_otp": otp})
    if not user:
        return jsonify({"success": False, "error": {"code": "INVALID_TOKEN", "message": "Invalid or expired reset code. Please start over."}}), 400
    
    expires = user.get("reset_expires")
    if expires and expires.tzinfo is None:
        from datetime import timezone as tz
        expires = expires.replace(tzinfo=tz.utc)
    
    if not expires or now > expires:
        return jsonify({"success": False, "error": {"code": "TOKEN_EXPIRED", "message": "Reset code has expired (15 min limit). Please start over."}}), 400
    
    # Update password and clear reset fields
    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": hash_password(new_password)},
         "$unset": {"reset_token": "", "reset_otp": "", "reset_expires": ""}}
    )
    
    return jsonify({"success": True, "message": "Password reset successfully. You can now log in with your new password."}), 200

@auth_bp.route("/me", methods=["GET"])
@token_required
def get_me(current_user):
    return jsonify({
        "success": True,
        "data": {
            "id": str(current_user["_id"]),
            "name": current_user.get("name"),
            "email": current_user.get("email"),
            "consumer_number": current_user.get("consumer_number", ""),
            "state": current_user.get("state", "Maharashtra"),
            "distributor": current_user.get("distributor", "MSEDCL"),
            "settings": current_user.get("settings", {
                "monthly_unit_threshold": 200,
                "monthly_budget": 1500,
                "alert_increase_pct": 20
            })
        }
    }), 200

@auth_bp.route("/me", methods=["PUT"])
@token_required
def update_me(current_user):
    data = request.get_json() or {}
    db = get_db()
    
    update_fields = {}
    if "name" in data:
        update_fields["name"] = data["name"].strip()
    if "consumer_number" in data:
        update_fields["consumer_number"] = data["consumer_number"].strip()
    if "state" in data:
        update_fields["state"] = data["state"].strip()
    if "distributor" in data:
        update_fields["distributor"] = data["distributor"].strip()
        
    if "settings" in data and isinstance(data["settings"], dict):
        settings = current_user.get("settings", {})
        settings.update(data["settings"])
        update_fields["settings"] = settings
        
    if update_fields:
        db.users.update_one({"_id": current_user["_id"]}, {"$set": update_fields})
        
    updated = db.users.find_one({"_id": current_user["_id"]})
    return jsonify({
        "success": True,
        "message": "Profile updated successfully",
        "data": {
            "id": str(updated["_id"]),
            "name": updated.get("name"),
            "email": updated.get("email"),
            "consumer_number": updated.get("consumer_number", ""),
            "settings": updated.get("settings", {})
        }
    }), 200
