"""
Bill management, what-if calculation, and OCR bill upload endpoints.
"""

import os
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, current_app
from bson import ObjectId
from datetime import datetime, timezone
from backend.config import Config
from backend.utils.db import get_db
from backend.utils.auth_guard import token_required
from backend.services.calculator import calculate_bill
from backend.services.ocr_parser import extract_bill_data

bills_bp = Blueprint("bills", __name__, url_prefix="/api/v1/bills")

DEFAULT_APPLIANCE_PROFILES = [
    {"name": "Air Conditioner", "watts": 1500, "hours_per_day": 6, "days_per_month": 25},
    {"name": "Refrigerator", "watts": 150, "hours_per_day": 24, "days_per_month": 30},
    {"name": "Water Heater (Geyser)", "watts": 2000, "hours_per_day": 1, "days_per_month": 25},
    {"name": "Ceiling Fans", "watts": 75, "hours_per_day": 10, "days_per_month": 30},
    {"name": "Television", "watts": 120, "hours_per_day": 6, "days_per_month": 30},
    {"name": "Washing Machine", "watts": 500, "hours_per_day": 1, "days_per_month": 15},
    {"name": "LED Lighting", "watts": 40, "hours_per_day": 6, "days_per_month": 30},
    {"name": "Laptop / Computer", "watts": 80, "hours_per_day": 5, "days_per_month": 25}
]

def bifurcate_bill_by_appliances(units, total_amount, user_id, db):
    """
    Distribute the bill total amount and total units across listed appliances
    proportionally based on their baseline energy consumption.
    """
    units = float(units or 0.0)
    total_amount = float(total_amount or 0.0)

    user_apps = list(db.appliances.find({"user_id": user_id})) if (user_id and db is not None) else []
    items = []

    if user_apps:
        for a in user_apps:
            watts = float(a.get("watts", 100))
            hours = float(a.get("hours_per_day", 1))
            days = float(a.get("days_per_month", 30))
            qty = int(a.get("quantity", 1))
            base_kwh = (watts * hours * days * qty) / 1000.0
            items.append({
                "name": a.get("name"),
                "watts": watts,
                "base_kwh": base_kwh,
                "quantity": qty
            })
    else:
        for p in DEFAULT_APPLIANCE_PROFILES:
            watts = float(p["watts"])
            hours = float(p["hours_per_day"])
            days = float(p["days_per_month"])
            base_kwh = (watts * hours * days) / 1000.0
            items.append({
                "name": p["name"],
                "watts": watts,
                "base_kwh": base_kwh,
                "quantity": 1
            })

    total_base_kwh = sum(i["base_kwh"] for i in items)

    bifurcated = []
    for item in items:
        share = (item["base_kwh"] / total_base_kwh) if total_base_kwh > 0 else 0.0
        allocated_kwh = round(share * units, 2)
        allocated_cost = round(share * total_amount, 2)
        share_pct = round(share * 100.0, 1)
        bifurcated.append({
            "name": item["name"],
            "watts": item["watts"],
            "quantity": item["quantity"],
            "allocated_kwh": allocated_kwh,
            "allocated_cost": allocated_cost,
            "share_percent": share_pct
        })

    bifurcated.sort(key=lambda x: x["allocated_cost"], reverse=True)
    return bifurcated

def _get_active_tariff_dict(user, db):
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
            "distributor": "MSEDCL",
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

def _trigger_alerts(user, bill_doc, db):
    """Evaluate alert rules against the newly added/updated bill"""
    user_id = user["_id"]
    units = bill_doc.get("units", 0)
    total = bill_doc.get("calculated_total", 0)
    settings = user.get("settings", {})
    threshold = float(settings.get("monthly_unit_threshold", 200))
    budget = float(settings.get("monthly_budget", 1500))
    allowed_spike_pct = float(settings.get("alert_increase_pct", 20))
    
    # 1. High usage threshold alert
    if units > threshold:
        db.alerts.insert_one({
            "user_id": user_id,
            "type": "high_usage",
            "title": "High Usage Alert",
            "message": f"Your consumption of {units:.0f} units exceeded your monthly limit of {threshold:.0f} units for {bill_doc.get('month')}.",
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        })
        
    # 2. Budget overrun alert
    if total > budget:
        db.alerts.insert_one({
            "user_id": user_id,
            "type": "budget",
            "title": "Budget Exceeded",
            "message": f"Calculated bill (₹{total:,.2f}) exceeded your set monthly budget of ₹{budget:,.2f}.",
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        })
        
    # 3. MoM Spike check
    previous_bills = list(db.bills.find({"user_id": user_id, "month": {"$lt": bill_doc.get("month")}}).sort("month", -1).limit(1))
    if previous_bills:
        last_bill = previous_bills[0]
        last_units = float(last_bill.get("units", 0))
        if last_units > 0:
            pct_inc = ((units - last_units) / last_units) * 100.0
            if pct_inc >= allowed_spike_pct:
                db.alerts.insert_one({
                    "user_id": user_id,
                    "type": "spike",
                    "title": "Consumption Spike",
                    "message": f"Usage rose by {pct_inc:.1f}% compared to {last_bill.get('month')} ({last_units:.0f} → {units:.0f} units).",
                    "is_read": False,
                    "created_at": datetime.now(timezone.utc)
                })

@bills_bp.route("/calculate", methods=["POST"])
def stateless_calculate():
    """Stateless what-if bill calculator"""
    data = request.get_json() or {}
    units = data.get("units")
    if units is None:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "units is required"}}), 400
        
    tariff = data.get("tariff")
    if not tariff:
        db = get_db()
        tariff = db.tariffs.find_one({"is_default": True})
        if not tariff:
            tariff = {
                "name": "MSEDCL Residential",
                "slabs": [
                    {"from": 0, "to": 100, "rate": 5.0},
                    {"from": 101, "to": 300, "rate": 10.0},
                    {"from": 301, "to": None, "rate": 14.0}
                ],
                "fixed_charge": 120.0,
                "duty_percent": 16.0,
                "other_charges": 0.0
            }
            
    rebate = float(data.get("rebate", 0.0))
    other_charges = float(data.get("other_charges", tariff.get("other_charges", 0.0)))
    
    result = calculate_bill(units, tariff, rebate=rebate, other_charges=other_charges)
    return jsonify({"success": True, "data": result}), 200

@bills_bp.route("/upload", methods=["POST"])
@token_required
def upload_bill_ocr(current_user):
    """Upload PDF/image bill, extract fields via OCR, return for user confirmation"""
    if "file" not in request.files:
        return jsonify({"success": False, "error": {"code": "FILE_MISSING", "message": "No file uploaded"}}), 400
        
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": {"code": "FILE_EMPTY", "message": "No selected file"}}), 400
        
    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in Config.ALLOWED_EXTENSIONS:
        return jsonify({"success": False, "error": {"code": "INVALID_FILE_TYPE", "message": f"Allowed extensions: {', '.join(Config.ALLOWED_EXTENSIONS)}"}}), 400
        
    saved_filename = f"{current_user['_id']}_{int(datetime.now().timestamp())}_{filename}"
    file_path = os.path.join(Config.UPLOAD_FOLDER, saved_filename)
    file.save(file_path)
    
    try:
        extracted = extract_bill_data(file_path)
        extracted["saved_filename"] = saved_filename
        
        # Pre-fill tariff simulation if units exist
        db = get_db()
        active_tariff = _get_active_tariff_dict(current_user, db)
        if extracted.get("units") is not None:
            calc = calculate_bill(extracted["units"], active_tariff)
            extracted["calculated_preview"] = calc
            
        total_for_bifurcation = extracted.get("total_amount") or (extracted.get("calculated_preview", {}).get("total") if extracted.get("calculated_preview") else 0)
        units_for_bifurcation = extracted.get("units") or 0
        extracted["appliance_bifurcation"] = bifurcate_bill_by_appliances(
            units_for_bifurcation, total_for_bifurcation, current_user["_id"], db
        )
            
        return jsonify({
            "success": True,
            "message": "Bill extracted successfully. Please review and confirm.",
            "data": extracted
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": {"code": "OCR_PARSER_ERROR", "message": f"Failed to extract text from bill: {str(e)}"},
            "data": {"saved_filename": saved_filename}
        }), 500

@bills_bp.route("", methods=["POST"])
@token_required
def create_bill(current_user):
    data = request.get_json() or {}
    month = data.get("month", "").strip()
    prev_reading = data.get("previous_reading")
    curr_reading = data.get("current_reading")
    units = data.get("units")
    actual_total = data.get("actual_total")
    rebate = float(data.get("rebate", 0.0))
    other_charges = float(data.get("other_charges", 0.0))
    source = data.get("source", "manual")
    file_name = data.get("file_name")
    
    if not month:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Billing month (YYYY-MM) is required"}}), 400
        
    # Validation: Reading logic
    if prev_reading is not None and curr_reading is not None:
        prev_reading = float(prev_reading)
        curr_reading = float(curr_reading)
        if curr_reading < prev_reading:
            return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Current meter reading must be ≥ previous reading"}}), 400
        computed_units = round(curr_reading - prev_reading, 2)
        if units is None:
            units = computed_units
    elif units is not None:
        units = float(units)
        prev_reading = float(prev_reading) if prev_reading is not None else 0.0
        curr_reading = prev_reading + units
    else:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Provide either meter readings or units consumed"}}), 400
        
    db = get_db()
    user_id = current_user["_id"]
    
    # Check duplicate month
    existing = db.bills.find_one({"user_id": user_id, "month": month})
    if existing:
        return jsonify({
            "success": False,
            "error": {"code": "DUPLICATE_MONTH", "message": f"A bill for {month} already exists. You can edit it from Bill History."}
        }), 400
        
    # Fetch active tariff and create immutable snapshot
    active_tariff = _get_active_tariff_dict(current_user, db)
    tariff_snapshot = {
        "name": active_tariff.get("name"),
        "distributor": active_tariff.get("distributor"),
        "slabs": active_tariff.get("slabs"),
        "fixed_charge": active_tariff.get("fixed_charge"),
        "duty_percent": active_tariff.get("duty_percent"),
        "other_charges": other_charges
    }
    
    calc_res = calculate_bill(units, active_tariff, rebate=rebate, other_charges=other_charges)
    final_amount = float(actual_total) if actual_total is not None else calc_res["total"]
    appliance_bifurcation = bifurcate_bill_by_appliances(units, final_amount, user_id, db)
    
    bill_doc = {
        "user_id": user_id,
        "month": month,
        "previous_reading": prev_reading,
        "current_reading": curr_reading,
        "units": units,
        "breakdown": {
            "slab_charges": calc_res["lines"],
            "energy_charge": calc_res["energy_charge"],
            "fixed_charge": calc_res["fixed_charge"],
            "duty": calc_res["duty"],
            "other_charges": other_charges,
            "rebate": rebate
        },
        "appliance_breakdown": appliance_bifurcation,
        "calculated_total": calc_res["total"],
        "actual_total": final_amount,
        "tariff_snapshot": tariff_snapshot,
        "source": source,
        "file_name": file_name,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    res = db.bills.insert_one(bill_doc)
    bill_doc["id"] = str(res.inserted_id)
    del bill_doc["_id"]
    bill_doc["user_id"] = str(bill_doc["user_id"])
    
    # Trigger smart alerts
    _trigger_alerts(current_user, bill_doc, db)
    
    return jsonify({
        "success": True,
        "message": "Bill added successfully",
        "data": bill_doc
    }), 201

@bills_bp.route("", methods=["GET"])
@token_required
def list_bills(current_user):
    db = get_db()
    user_id = current_user["_id"]
    
    year = request.args.get("year")
    from_m = request.args.get("from")
    to_m = request.args.get("to")
    
    query = {"user_id": user_id}
    if year:
        query["month"] = {"$regex": f"^{year}"}
    if from_m and to_m:
        query["month"] = {"$gte": from_m, "$lte": to_m}
    elif from_m:
        query["month"] = {"$gte": from_m}
    elif to_m:
        query["month"] = {"$lte": to_m}
        
    bills = list(db.bills.find(query).sort("month", -1))
    
    results = []
    for b in bills:
        results.append({
            "id": str(b["_id"]),
            "month": b.get("month"),
            "previous_reading": b.get("previous_reading"),
            "current_reading": b.get("current_reading"),
            "units": b.get("units"),
            "calculated_total": b.get("calculated_total"),
            "actual_total": b.get("actual_total"),
            "breakdown": b.get("breakdown"),
            "source": b.get("source"),
            "file_name": b.get("file_name"),
            "created_at": b.get("created_at").isoformat() if b.get("created_at") else None
        })
        
    return jsonify({"success": True, "data": results}), 200

@bills_bp.route("/<bill_id>", methods=["GET"])
@token_required
def get_bill_detail(current_user, bill_id):
    db = get_db()
    try:
        b_obj = ObjectId(bill_id)
    except Exception:
        b_obj = bill_id
        
    bill = db.bills.find_one({"_id": b_obj, "user_id": current_user["_id"]})
    if not bill:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Bill not found"}}), 404
        
    bill["id"] = str(bill["_id"])
    del bill["_id"]
    bill["user_id"] = str(bill["user_id"])
    if not bill.get("appliance_breakdown"):
        units_val = bill.get("units", 0)
        total_val = bill.get("actual_total") or bill.get("calculated_total", 0)
        bill["appliance_breakdown"] = bifurcate_bill_by_appliances(units_val, total_val, current_user["_id"], db)
    if bill.get("created_at"):
        bill["created_at"] = bill["created_at"].isoformat()
    if bill.get("updated_at"):
        bill["updated_at"] = bill["updated_at"].isoformat()
        
    return jsonify({"success": True, "data": bill}), 200

@bills_bp.route("/<bill_id>", methods=["PUT"])
@token_required
def update_bill(current_user, bill_id):
    data = request.get_json() or {}
    db = get_db()
    try:
        b_obj = ObjectId(bill_id)
    except Exception:
        b_obj = bill_id
        
    existing = db.bills.find_one({"_id": b_obj, "user_id": current_user["_id"]})
    if not existing:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Bill not found"}}), 404
        
    prev_reading = float(data.get("previous_reading", existing.get("previous_reading", 0)))
    curr_reading = float(data.get("current_reading", existing.get("current_reading", 0)))
    units = float(data.get("units", curr_reading - prev_reading))
    actual_total = float(data.get("actual_total", existing.get("actual_total", 0)))
    rebate = float(data.get("rebate", existing.get("breakdown", {}).get("rebate", 0.0)))
    other_charges = float(data.get("other_charges", existing.get("breakdown", {}).get("other_charges", 0.0)))
    
    tariff = existing.get("tariff_snapshot") or _get_active_tariff_dict(current_user, db)
    calc_res = calculate_bill(units, tariff, rebate=rebate, other_charges=other_charges)
    
    update_doc = {
        "previous_reading": prev_reading,
        "current_reading": curr_reading,
        "units": units,
        "actual_total": actual_total,
        "calculated_total": calc_res["total"],
        "breakdown": {
            "slab_charges": calc_res["lines"],
            "energy_charge": calc_res["energy_charge"],
            "fixed_charge": calc_res["fixed_charge"],
            "duty": calc_res["duty"],
            "other_charges": other_charges,
            "rebate": rebate
        },
        "updated_at": datetime.now(timezone.utc)
    }
    
    db.bills.update_one({"_id": b_obj}, {"$set": update_doc})
    return jsonify({"success": True, "message": "Bill updated successfully"}), 200

@bills_bp.route("/<bill_id>", methods=["DELETE"])
@token_required
def delete_bill(current_user, bill_id):
    db = get_db()
    try:
        b_obj = ObjectId(bill_id)
    except Exception:
        b_obj = bill_id
        
    res = db.bills.delete_one({"_id": b_obj, "user_id": current_user["_id"]})
    if res.deleted_count == 0:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Bill not found"}}), 404
        
    return jsonify({"success": True, "message": "Bill deleted successfully"}), 200
