"""
PDF Report generation and download routes.
"""

from flask import Blueprint, request, jsonify, send_file
from bson import ObjectId
from backend.utils.db import get_db
from backend.utils.auth_guard import token_required
from backend.services.pdf_generator import generate_pdf_report
from backend.services.predictor import predict_next_bill
from backend.services.tips_engine import generate_energy_tips

reports_bp = Blueprint("reports", __name__, url_prefix="/api/v1/reports")

@reports_bp.route("/pdf", methods=["GET"])
@token_required
def download_pdf_report(current_user):
    month = request.args.get("month")
    bill_id = request.args.get("bill_id")
    db = get_db()
    user_id = current_user["_id"]
    
    # Locate target bill
    bill = None
    if bill_id:
        try:
            bill = db.bills.find_one({"_id": ObjectId(bill_id), "user_id": user_id})
        except Exception:
            bill = db.bills.find_one({"_id": bill_id, "user_id": user_id})
    elif month:
        bill = db.bills.find_one({"month": month, "user_id": user_id})
    else:
        # Default to latest bill
        bill = db.bills.find_one({"user_id": user_id}, sort=[("month", -1)])
        
    if not bill:
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "No bill found to generate report for. Please add a bill first."}}), 404
        
    bills_history = list(db.bills.find({"user_id": user_id}).sort("month", 1))
    appliances = list(db.appliances.find({"user_id": user_id}))
    
    # Active tariff
    active_id = current_user.get("active_tariff_id")
    tariff = None
    if active_id:
        try:
            tariff = db.tariffs.find_one({"_id": ObjectId(active_id)})
        except Exception:
            tariff = db.tariffs.find_one({"_id": active_id})
    if not tariff:
        tariff = db.tariffs.find_one({"is_default": True})
        
    prediction = predict_next_bill(bills_history, tariff or {})
    tips = generate_energy_tips(bills_history, appliances, tariff or {})
    
    pdf_stream = generate_pdf_report(
        user=current_user,
        bill=bill,
        bills_history=bills_history,
        appliances=appliances,
        prediction=prediction,
        tips=tips
    )
    
    download_name = f"Electricity_Report_{bill.get('month', 'latest')}.pdf"
    
    return send_file(
        pdf_stream,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=download_name
    )
