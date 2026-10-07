"""
In-app alerts and notifications endpoints.
"""

from flask import Blueprint, jsonify
from bson import ObjectId
from backend.utils.db import get_db
from backend.utils.auth_guard import token_required

alerts_bp = Blueprint("alerts", __name__, url_prefix="/api/v1/alerts")

@alerts_bp.route("", methods=["GET"])
@token_required
def list_alerts(current_user):
    db = get_db()
    user_id = current_user["_id"]
    
    alerts = list(db.alerts.find({"user_id": user_id}).sort("created_at", -1).limit(20))
    
    res = []
    unread_count = 0
    for a in alerts:
        is_read = a.get("is_read", False)
        if not is_read:
            unread_count += 1
        res.append({
            "id": str(a["_id"]),
            "type": a.get("type", "info"),
            "title": a.get("title", "Notification"),
            "message": a.get("message"),
            "is_read": is_read,
            "created_at": a.get("created_at").isoformat() if a.get("created_at") else None
        })
        
    return jsonify({
        "success": True,
        "data": {
            "alerts": res,
            "unread_count": unread_count
        }
    }), 200

@alerts_bp.route("/<alert_id>/read", methods=["PATCH"])
@token_required
def mark_alert_read(current_user, alert_id):
    db = get_db()
    try:
        a_obj = ObjectId(alert_id)
    except Exception:
        a_obj = alert_id
        
    db.alerts.update_one(
        {"_id": a_obj, "user_id": current_user["_id"]},
        {"$set": {"is_read": True}}
    )
    return jsonify({"success": True, "message": "Alert marked as read"}), 200

@alerts_bp.route("/read-all", methods=["POST"])
@token_required
def mark_all_alerts_read(current_user):
    db = get_db()
    db.alerts.update_many(
        {"user_id": current_user["_id"]},
        {"$set": {"is_read": True}}
    )
    return jsonify({"success": True, "message": "All alerts marked as read"}), 200
