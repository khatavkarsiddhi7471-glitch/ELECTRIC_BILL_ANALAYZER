"""
Energy-saving recommendations endpoints.
"""

from flask import Blueprint, jsonify
from bson import ObjectId
from backend.utils.db import get_db
from backend.utils.auth_guard import token_required
from backend.services.tips_engine import generate_energy_tips

tips_bp = Blueprint("tips", __name__, url_prefix="/api/v1/tips")

@tips_bp.route("", methods=["GET"])
@token_required
def get_tips(current_user):
    db = get_db()
    user_id = current_user["_id"]
    
    bills = list(db.bills.find({"user_id": user_id}).sort("month", 1))
    appliances = list(db.appliances.find({"user_id": user_id}))
    
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
        tariff = {
            "slabs": [
                {"from": 0, "to": 100, "rate": 5.0},
                {"from": 101, "to": 300, "rate": 10.0},
                {"from": 301, "to": None, "rate": 14.0}
            ]
        }
        
    tips = generate_energy_tips(bills, appliances, tariff)
    
    total_potential_savings = sum(t.get("estimated_monthly_savings_inr", 0) for t in tips)
    total_potential_kwh = sum(t.get("estimated_kwh_savings", 0) for t in tips)
    
    return jsonify({
        "success": True,
        "data": {
            "tips": tips,
            "total_potential_monthly_savings_inr": total_potential_savings,
            "total_potential_kwh_savings": round(total_potential_kwh, 1),
            "tips_count": len(tips)
        }
    }), 200
