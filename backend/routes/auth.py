"""
Authentication and user profile endpoints.

Password Reset Flow (production-ready):
  1. POST /api/v1/auth/forgot-password
       - Generates crypto-secure random token
       - Stores SHA-256(token) in MongoDB with 15-min expiry
       - Emails reset URL containing the raw token via Gmail API
  2. POST /api/v1/auth/reset-password/<token>
       - Hashes the incoming URL token with SHA-256
       - Looks up matching, non-expired record in MongoDB
       - Updates password (bcrypt), clears reset fields
"""

import os
import hashlib
import secrets
import re
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify
from bson import ObjectId

from backend.utils.db import get_db
from backend.utils.auth_guard import hash_password, check_password, generate_token, token_required
from backend.utils.email_service import send_password_reset_email

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

# ── Helpers ────────────────────────────────────────────────────────────────────

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5000")
EMAIL_REGEX   = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _sha256(token: str) -> str:
    """SHA-256 hash a string token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ── Register ───────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
def register():
    data    = request.get_json() or {}
    name    = data.get("name", "").strip()
    email   = data.get("email", "").strip().lower()
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
    if db.users.find_one({"email": email}):
        return jsonify({
            "success": False,
            "error": {"code": "EMAIL_EXISTS", "message": "An account with this email already exists"}
        }), 400

    default_tariff   = db.tariffs.find_one({"user_id": None, "is_default": True})
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
        "created_at": datetime.now(timezone.utc),
        # Password-reset fields (always present, null by default)
        "reset_password_token":   None,
        "reset_password_expires": None,
    }

    res     = db.users.insert_one(user_doc)
    user_id = str(res.inserted_id)
    token   = generate_token(user_id, email)

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


# ── Login ──────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
def login():
    data     = request.get_json() or {}
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "success": False,
            "error": {"code": "VALIDATION_ERROR", "message": "Email and password are required"}
        }), 400

    db   = get_db()
    user = db.users.find_one({"email": email})
    if not user or not check_password(password, user.get("password_hash", "")):
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"}
        }), 401

    user_id = str(user["_id"])
    token   = generate_token(user_id, email)

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


# ── Forgot Password ────────────────────────────────────────────────────────────

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """
    POST /api/v1/auth/forgot-password
    Body: { "email": "user@example.com" }

    Security properties:
    - Email enumeration protection: same response for registered and unregistered emails
    - Cryptographically secure token: secrets.token_hex(32) == 64 hex chars
    - Only SHA-256(token) is stored in MongoDB — raw token never persisted
    - Token valid for 15 minutes
    - Reset URL contains the raw token (sent to user's inbox via Gmail API)
    """
    data  = request.get_json() or {}
    email = data.get("email", "").strip().lower()

    # Validate email format
    if not email or not EMAIL_REGEX.match(email):
        return jsonify({
            "success": False,
            "error": {"code": "VALIDATION_ERROR", "message": "Please enter a valid email address."}
        }), 400

    # Generic success message — used for both found and not-found cases
    GENERIC_MSG = "If an account exists with this email, a password reset link has been sent."

    db   = get_db()
    user = db.users.find_one({"email": email})

    if not user:
        # Email not registered — return generic response (no enumeration)
        return jsonify({"success": True, "message": GENERIC_MSG}), 200

    # ── Generate secure token ──────────────────────────────────────────────────
    raw_token    = secrets.token_hex(32)          # 64-char hex, never stored
    hashed_token = _sha256(raw_token)             # only this goes into MongoDB
    expires_at   = datetime.now(timezone.utc) + timedelta(minutes=15)

    # ── Store hashed token + expiry on user document ───────────────────────────
    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "reset_password_token":   hashed_token,
            "reset_password_expires": expires_at,
        }}
    )

    # ── Build reset URL (raw token in URL — never the hash) ───────────────────
    reset_url = f"{FRONTEND_URL}/reset-password.html?token={raw_token}"
    user_name = user.get("name", "Valued User")

    # ── Send via Gmail API ─────────────────────────────────────────────────────
    mail_result = send_password_reset_email(email, user_name, reset_url)

    if not mail_result.get("success"):
        # Log on backend; return safe generic error to client
        return jsonify({
            "success": False,
            "error": {
                "code": "EMAIL_SEND_FAILED",
                "message": "Unable to send reset email. Please try again later."
            }
        }), 500

    return jsonify({"success": True, "message": GENERIC_MSG}), 200


# ── Reset Password ─────────────────────────────────────────────────────────────

@auth_bp.route("/reset-password/<string:token>", methods=["POST"])
def reset_password(token):
    """
    POST /api/v1/auth/reset-password/<raw_token>
    Body: { "password": "NewSecurePassword1!" }

    Security properties:
    - Incoming token is SHA-256 hashed before DB lookup
    - Expiry enforced server-side
    - After successful reset: token fields set to null (one-time use)
    - Password hashed with bcrypt (same as rest of app)
    """
    data         = request.get_json() or {}
    new_password = data.get("password", "")

    # ── Validate new password ──────────────────────────────────────────────────
    if not new_password or len(new_password) < 8:
        return jsonify({
            "success": False,
            "error": {"code": "VALIDATION_ERROR", "message": "Password must be at least 8 characters."}
        }), 400

    if not token or len(token) < 16:
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_TOKEN", "message": "Reset link is invalid or has expired."}
        }), 400

    # ── Hash the incoming raw token for lookup ─────────────────────────────────
    hashed_token = _sha256(token)
    now          = datetime.now(timezone.utc)

    db   = get_db()
    user = db.users.find_one({"reset_password_token": hashed_token})

    if not user:
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_TOKEN", "message": "Reset link is invalid or has expired."}
        }), 400

    # ── Check expiration ───────────────────────────────────────────────────────
    expires = user.get("reset_password_expires")
    if expires is None:
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_TOKEN", "message": "Reset link is invalid or has expired."}
        }), 400

    # Ensure timezone-aware comparison
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if now > expires:
        return jsonify({
            "success": False,
            "error": {"code": "TOKEN_EXPIRED", "message": "This password reset link has expired. Please request a new one."}
        }), 400

    # ── Update password + invalidate token (one-time use) ─────────────────────
    db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set":   {"password_hash": hash_password(new_password)},
            "$unset": {
                "reset_password_token":   "",
                "reset_password_expires": "",
                # Also clear any legacy OTP fields from old implementation
                "reset_token":   "",
                "reset_otp":     "",
                "reset_expires": "",
            }
        }
    )

    return jsonify({
        "success": True,
        "message": "Password reset successfully. You can now sign in with your new password."
    }), 200


# ── Profile (GET) ──────────────────────────────────────────────────────────────

@auth_bp.route("/me", methods=["GET"])
@token_required
def get_me(current_user):
    return jsonify({
        "success": True,
        "data": {
            "id":              str(current_user["_id"]),
            "name":            current_user.get("name"),
            "email":           current_user.get("email"),
            "consumer_number": current_user.get("consumer_number", ""),
            "state":           current_user.get("state", "Maharashtra"),
            "distributor":     current_user.get("distributor", "MSEDCL"),
            "settings":        current_user.get("settings", {
                "monthly_unit_threshold": 200,
                "monthly_budget": 1500,
                "alert_increase_pct": 20
            })
        }
    }), 200


# ── Profile (PUT) ──────────────────────────────────────────────────────────────

@auth_bp.route("/me", methods=["PUT"])
@token_required
def update_me(current_user):
    data = request.get_json() or {}
    db   = get_db()

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
            "id":              str(updated["_id"]),
            "name":            updated.get("name"),
            "email":           updated.get("email"),
            "consumer_number": updated.get("consumer_number", ""),
            "settings":        updated.get("settings", {})
        }
    }), 200
