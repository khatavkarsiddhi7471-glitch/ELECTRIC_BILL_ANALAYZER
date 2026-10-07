"""
Tariff profile management routes.
"""

from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime, timezone
from backend.utils.db import get_db
from backend.utils.auth_guard import token_required

tariffs_bp = Blueprint("tariffs", __name__, url_prefix="/api/v1/tariffs")

@tariffs_bp.route("", methods=["GET"])
@token_required
def get_tariffs(current_user):
    db = get_db()
    user_id = current_user["_id"]
    
    # Fetch system default tariffs and user's custom tariffs
    tariffs = list(db.tariffs.find({
        "$or": [
            {"user_id": None},
            {"user_id": user_id}
        ]
    }))
    
    active_tariff_id = current_user.get("active_tariff_id")
    
    res = []
    for t in tariffs:
        t_id = str(t["_id"])
        res.append({
            "id": t_id,
            "name": t.get("name"),
            "distributor": t.get("distributor"),
            "category": t.get("category"),
            "slabs": t.get("slabs", []),
            "fixed_charge": t.get("fixed_charge", 0),
            "duty_percent": t.get("duty_percent", 0),
            "other_charges": t.get("other_charges", 0),
            "is_default": t.get("is_default", False),
            "is_active": str(active_tariff_id) == t_id if active_tariff_id else t.get("is_default", False)
        })
        
    return jsonify({"success": True, "data": res}), 200

@tariffs_bp.route("/active", methods=["GET"])
@token_required
def get_active_tariff(current_user):
    db = get_db()
    active_id = current_user.get("active_tariff_id")
    tariff = None
    
    if active_id:
        try:
            tariff = db.tariffs.find_one({"_id": ObjectId(active_id)})
        except Exception:
            tariff = db.tariffs.find_one({"_id": active_id})
            
    if not tariff:
        tariff = db.tariffs.find_one({"is_default": True})
        
    if not tariff:
        # Fallback default MSEDCL
        tariff = {
            "name": "MSEDCL Residential",
            "distributor": "MSEDCL",
            "category": "LT-I Residential",
            "slabs": [
                {"from": 0, "to": 100, "rate": 5.0},
                {"from": 101, "to": 300, "rate": 10.0},
                {"from": 301, "to": None, "rate": 14.0}
            ],
            "fixed_charge": 120.0,
            "duty_percent": 16.0,
            "other_charges": 0.0
        }
    else:
        tariff["id"] = str(tariff["_id"])
        if "_id" in tariff:
            del tariff["_id"]
            
    return jsonify({"success": True, "data": tariff}), 200

@tariffs_bp.route("/active", methods=["PUT"])
@token_required
def set_active_tariff(current_user):
    data = request.get_json() or {}
    tariff_id = data.get("tariff_id")
    if not tariff_id:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "tariff_id required"}}), 400
        
    db = get_db()
    try:
        t_obj = ObjectId(tariff_id)
    except Exception:
        t_obj = tariff_id
        
    tariff = db.tariffs.find_one({"_id": t_obj})
    if not tariff:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Tariff not found"}}), 404
        
    db.users.update_one({"_id": current_user["_id"]}, {"$set": {"active_tariff_id": t_obj}})
    return jsonify({"success": True, "message": "Active tariff updated", "data": {"active_tariff_id": str(t_obj)}}), 200

@tariffs_bp.route("", methods=["POST"])
@token_required
def create_custom_tariff(current_user):
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    distributor = data.get("distributor", "").strip()
    slabs = data.get("slabs", [])
    fixed_charge = float(data.get("fixed_charge", 0))
    duty_percent = float(data.get("duty_percent", 0))
    other_charges = float(data.get("other_charges", 0))
    
    if not name or not slabs:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Tariff name and slabs are required"}}), 400
        
    tariff_doc = {
        "user_id": current_user["_id"],
        "name": name,
        "distributor": distributor,
        "category": data.get("category", "Residential"),
        "slabs": slabs,
        "fixed_charge": fixed_charge,
        "duty_percent": duty_percent,
        "other_charges": other_charges,
        "is_default": False,
        "created_at": datetime.now(timezone.utc)
    }
    
    db = get_db()
    res = db.tariffs.insert_one(tariff_doc)
    tariff_doc["id"] = str(res.inserted_id)
    del tariff_doc["_id"]
    if "user_id" in tariff_doc:
        tariff_doc["user_id"] = str(tariff_doc["user_id"])
        
    return jsonify({"success": True, "message": "Custom tariff created", "data": tariff_doc}), 201
