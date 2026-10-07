"""
Appliance-wise cost estimator and inventory routes.
"""

from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime, timezone
from backend.utils.db import get_db
from backend.utils.auth_guard import token_required

appliances_bp = Blueprint("appliances", __name__, url_prefix="/api/v1/appliances")

PRESET_CATALOG = [
    {"name": "Split Air Conditioner (1.5 Ton, 3 Star)", "watts": 1500, "category": "Cooling", "typical_hours": 8},
    {"name": "Inverter AC (1.5 Ton, 5 Star)", "watts": 1000, "category": "Cooling", "typical_hours": 8},
    {"name": "Refrigerator (Double Door, 260L)", "watts": 200, "category": "Refrigeration", "typical_hours": 24},
    {"name": "Ceiling Fan (BLDC 5-Star)", "watts": 28, "category": "Ventilation", "typical_hours": 12},
    {"name": "Ceiling Fan (Standard Induction)", "watts": 75, "category": "Ventilation", "typical_hours": 12},
    {"name": "LED Bulb (9W)", "watts": 9, "category": "Lighting", "typical_hours": 6},
    {"name": "Instant Water Geyser (3kW)", "watts": 3000, "category": "Heating", "typical_hours": 0.5},
    {"name": "Storage Geyser (25L, 2kW)", "watts": 2000, "category": "Heating", "typical_hours": 1.0},
    {"name": "Front Load Washing Machine", "watts": 1000, "category": "Cleaning", "typical_hours": 1.0},
    {"name": "Smart LED TV 55-inch", "watts": 110, "category": "Entertainment", "typical_hours": 5},
    {"name": "Microwave Oven", "watts": 1200, "category": "Kitchen", "typical_hours": 0.5},
    {"name": "Desktop Computer / Workstation", "watts": 250, "category": "Office", "typical_hours": 8},
    {"name": "Laptop Charger", "watts": 65, "category": "Office", "typical_hours": 6}
]

def _calculate_appliance_metrics(watts, hours_per_day, days_per_month, quantity, marginal_rate=8.5):
    """
    Formula: Monthly kWh = (Watts * Hours/Day * Days * Qty) / 1000
    Estimated Cost = Monthly kWh * marginal rate
    """
    watts = float(watts)
    hours = float(hours_per_day)
    days = float(days_per_month)
    qty = int(quantity)
    
    monthly_kwh = round((watts * hours * days * qty) / 1000.0, 2)
    estimated_cost = round(monthly_kwh * marginal_rate, 2)
    return monthly_kwh, estimated_cost

@appliances_bp.route("/catalog", methods=["GET"])
def get_catalog():
    return jsonify({"success": True, "data": PRESET_CATALOG}), 200

@appliances_bp.route("", methods=["GET"])
@token_required
def list_appliances(current_user):
    db = get_db()
    user_id = current_user["_id"]
    
    appliances = list(db.appliances.find({"user_id": user_id}))
    res = []
    for a in appliances:
        res.append({
            "id": str(a["_id"]),
            "name": a.get("name"),
            "watts": a.get("watts"),
            "hours_per_day": a.get("hours_per_day"),
            "days_per_month": a.get("days_per_month", 30),
            "quantity": a.get("quantity", 1),
            "monthly_kwh": a.get("monthly_kwh", 0),
            "estimated_cost": a.get("estimated_cost", 0)
        })
        
    return jsonify({"success": True, "data": res}), 200

@appliances_bp.route("/summary", methods=["GET"])
@token_required
def get_appliances_summary(current_user):
    db = get_db()
    user_id = current_user["_id"]
    
    appliances = list(db.appliances.find({"user_id": user_id}))
    if not appliances:
        return jsonify({
            "success": True,
            "data": {
                "total_appliances": 0,
                "total_estimated_kwh": 0,
                "total_estimated_cost": 0,
                "top_consumer": None,
                "rankings": []
            }
        }), 200
        
    total_kwh = sum(float(a.get("monthly_kwh", 0)) for a in appliances)
    total_cost = sum(float(a.get("estimated_cost", 0)) for a in appliances)
    
    sorted_apps = sorted(appliances, key=lambda x: float(x.get("monthly_kwh", 0)), reverse=True)
    
    rankings = []
    for a in sorted_apps:
        kwh = float(a.get("monthly_kwh", 0))
        share = round((kwh / total_kwh * 100.0), 1) if total_kwh > 0 else 0.0
        rankings.append({
            "id": str(a["_id"]),
            "name": a.get("name"),
            "watts": a.get("watts"),
            "monthly_kwh": kwh,
            "estimated_cost": float(a.get("estimated_cost", 0)),
            "share_percent": share,
            "is_high_consumer": share >= 25.0
        })
        
    top_consumer = rankings[0] if rankings else None
    
    return jsonify({
        "success": True,
        "data": {
            "total_appliances": len(appliances),
            "total_estimated_kwh": round(total_kwh, 1),
            "total_estimated_cost": round(total_cost, 2),
            "top_consumer": top_consumer,
            "rankings": rankings
        }
    }), 200

@appliances_bp.route("", methods=["POST"])
@token_required
def add_appliance(current_user):
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    watts = data.get("watts")
    hours = data.get("hours_per_day", 1)
    days = data.get("days_per_month", 30)
    qty = data.get("quantity", 1)
    marginal_rate = float(data.get("marginal_rate", 8.5))
    
    if not name or watts is None:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Name and wattage are required"}}), 400
        
    monthly_kwh, estimated_cost = _calculate_appliance_metrics(watts, hours, days, qty, marginal_rate)
    
    doc = {
        "user_id": current_user["_id"],
        "name": name,
        "watts": float(watts),
        "hours_per_day": float(hours),
        "days_per_month": float(days),
        "quantity": int(qty),
        "monthly_kwh": monthly_kwh,
        "estimated_cost": estimated_cost,
        "created_at": datetime.now(timezone.utc)
    }
    
    db = get_db()
    res = db.appliances.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    del doc["_id"]
    doc["user_id"] = str(doc["user_id"])
    
    return jsonify({"success": True, "message": "Appliance added", "data": doc}), 201

@appliances_bp.route("/<app_id>", methods=["DELETE"])
@token_required
def delete_appliance(current_user, app_id):
    db = get_db()
    try:
        a_obj = ObjectId(app_id)
    except Exception:
        a_obj = app_id
        
    res = db.appliances.delete_one({"_id": a_obj, "user_id": current_user["_id"]})
    if res.deleted_count == 0:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Appliance not found"}}), 404
        
    return jsonify({"success": True, "message": "Appliance removed"}), 200
