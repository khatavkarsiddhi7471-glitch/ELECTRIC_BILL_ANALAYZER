"""
Analytics, consumption trends, and prediction endpoints.
"""

from flask import Blueprint, jsonify
from datetime import datetime
from bson import ObjectId
from backend.utils.db import get_db
from backend.utils.auth_guard import token_required
from backend.services.predictor import predict_next_bill

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/v1")

def _get_active_tariff(user, db):
    active_id = user.get("active_tariff_id")
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
            "name": "MSEDCL Residential (Default)",
            "slabs": [
                {"from": 0, "to": 100, "rate": 5.0},
                {"from": 101, "to": 300, "rate": 10.0},
                {"from": 301, "to": None, "rate": 14.0}
            ],
            "fixed_charge": 120.0,
            "duty_percent": 16.0,
            "other_charges": 0.0
        }
    return tariff

@analytics_bp.route("/analytics/summary", methods=["GET"])
@token_required
def get_analytics_summary(current_user):
    db = get_db()
    user_id = current_user["_id"]
    
    bills = list(db.bills.find({"user_id": user_id}).sort("month", 1))
    
    if not bills:
        return jsonify({
            "success": True,
            "data": {
                "total_bills": 0,
                "latest_month": None,
                "latest_units": 0,
                "latest_amount": 0,
                "avg_monthly_units": 0,
                "avg_monthly_bill": 0,
                "avg_cost_per_kwh": 0,
                "highest_month": None,
                "lowest_month": None,
                "mom_unit_change_pct": 0,
                "mom_cost_change_pct": 0
            }
        }), 200
        
    units_list = [float(b.get("units", 0)) for b in bills]
    amounts_list = [float(b.get("calculated_total", 0)) for b in bills]
    
    total_units = sum(units_list)
    total_amount = sum(amounts_list)
    avg_units = round(total_units / len(bills), 1)
    avg_bill = round(total_amount / len(bills), 2)
    avg_cost_per_kwh = round(total_amount / total_units, 2) if total_units > 0 else 0.0
    
    max_idx = units_list.index(max(units_list))
    min_idx = units_list.index(min(units_list))
    
    highest_month = {
        "month": bills[max_idx].get("month"),
        "units": units_list[max_idx],
        "amount": amounts_list[max_idx]
    }
    
    lowest_month = {
        "month": bills[min_idx].get("month"),
        "units": units_list[min_idx],
        "amount": amounts_list[min_idx]
    }
    
    latest_bill = bills[-1]
    latest_units = float(latest_bill.get("units", 0))
    latest_amount = float(latest_bill.get("calculated_total", 0))
    
    mom_unit_change_pct = 0.0
    mom_cost_change_pct = 0.0
    if len(bills) >= 2:
        prev_bill = bills[-2]
        prev_u = float(prev_bill.get("units", 0))
        prev_a = float(prev_bill.get("calculated_total", 0))
        if prev_u > 0:
            mom_unit_change_pct = round(((latest_units - prev_u) / prev_u) * 100.0, 1)
        if prev_a > 0:
            mom_cost_change_pct = round(((latest_amount - prev_a) / prev_a) * 100.0, 1)
            
    return jsonify({
        "success": True,
        "data": {
            "total_bills": len(bills),
            "latest_month": latest_bill.get("month"),
            "latest_units": latest_units,
            "latest_amount": latest_amount,
            "avg_monthly_units": avg_units,
            "avg_monthly_bill": avg_bill,
            "avg_cost_per_kwh": avg_cost_per_kwh,
            "highest_month": highest_month,
            "lowest_month": lowest_month,
            "mom_unit_change_pct": mom_unit_change_pct,
            "mom_cost_change_pct": mom_cost_change_pct
        }
    }), 200

@analytics_bp.route("/analytics/charts", methods=["GET"])
@token_required
def get_chart_datasets(current_user):
    db = get_db()
    user_id = current_user["_id"]
    
    bills = list(db.bills.find({"user_id": user_id}).sort("month", 1))
    
    months = [b.get("month") for b in bills]
    units = [float(b.get("units", 0)) for b in bills]
    amounts = [float(b.get("calculated_total", 0)) for b in bills]
    energy_charges = [float(b.get("breakdown", {}).get("energy_charge", 0)) for b in bills]
    fixed_charges = [float(b.get("breakdown", {}).get("fixed_charge", 0)) for b in bills]
    duties = [float(b.get("breakdown", {}).get("duty", 0)) for b in bills]
    
    # Appliances breakdown
    appliances = list(db.appliances.find({"user_id": user_id}))
    app_labels = [a.get("name") for a in appliances]
    app_kwh = [float(a.get("monthly_kwh", 0)) for a in appliances]
    app_cost = [float(a.get("estimated_cost", 0)) for a in appliances]
    
    return jsonify({
        "success": True,
        "data": {
            "trend": {
                "labels": months,
                "units": units,
                "amounts": amounts
            },
            "composition": {
                "labels": months,
                "energy_charge": energy_charges,
                "fixed_charge": fixed_charges,
                "duty": duties
            },
            "appliances": {
                "labels": app_labels,
                "kwh": app_kwh,
                "cost": app_cost
            }
        }
    }), 200

@analytics_bp.route("/predict", methods=["GET"])
@token_required
def get_prediction(current_user):
    db = get_db()
    user_id = current_user["_id"]
    
    bills = list(db.bills.find({"user_id": user_id}).sort("month", 1))
    active_tariff = _get_active_tariff(current_user, db)
    
    prediction = predict_next_bill(bills, active_tariff)
    return jsonify({"success": True, "data": prediction}), 200
