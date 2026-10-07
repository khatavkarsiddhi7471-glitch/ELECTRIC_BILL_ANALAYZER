"""
Seed script to populate a test account with 6 months of historical bills,
appliances catalog, alerts, and active tariffs for testing & demonstration.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from backend.utils.db import get_db
from backend.utils.auth_guard import hash_password
from backend.services.calculator import calculate_bill

def seed_demo_data():
    db = get_db()
    
    # 1. Clean existing demo data
    demo_email = "demo@voltwise.com"
    db.users.delete_many({"email": demo_email})
    
    # 2. Get default tariff
    tariff = db.tariffs.find_one({"is_default": True})
    if not tariff:
        tariff = {
            "name": "MSEDCL Residential",
            "distributor": "MSEDCL",
            "slabs": [
                {"from": 0, "to": 100, "rate": 5.0},
                {"from": 101, "to": 300, "rate": 10.0},
                {"from": 301, "to": None, "rate": 14.0}
            ],
            "fixed_charge": 120.0,
            "duty_percent": 16.0,
            "other_charges": 0.0,
            "is_default": True
        }
        res_t = db.tariffs.insert_one(tariff)
        tariff["_id"] = res_t.inserted_id

    # 3. Create demo user
    user_doc = {
        "name": "Ravi Patil",
        "email": demo_email,
        "password_hash": hash_password("password123"),
        "consumer_number": "028710398421",
        "active_tariff_id": tariff["_id"],
        "state": "Maharashtra",
        "distributor": "MSEDCL",
        "settings": {
            "monthly_unit_threshold": 220,
            "monthly_budget": 1800,
            "alert_increase_pct": 20
        },
        "created_at": datetime.now(timezone.utc)
    }
    user_res = db.users.insert_one(user_doc)
    user_id = user_res.inserted_id

    # 4. Create 6 months of bills
    sample_bills = [
        {"month": "2026-01", "prev": 1000, "curr": 1130, "units": 130, "actual": 1110.0},
        {"month": "2026-02", "prev": 1130, "curr": 1275, "units": 145, "actual": 1250.0},
        {"month": "2026-03", "prev": 1275, "curr": 1425, "units": 150, "actual": 1300.0},
        {"month": "2026-04", "prev": 1425, "curr": 1605, "units": 180, "actual": 1610.0},
        {"month": "2026-05", "prev": 1605, "curr": 1815, "units": 210, "actual": 1950.0},
        {"month": "2026-06", "prev": 1815, "curr": 2045, "units": 230, "actual": 2180.0}
    ]

    for b in sample_bills:
        calc = calculate_bill(b["units"], tariff)
        db.bills.insert_one({
            "user_id": user_id,
            "month": b["month"],
            "previous_reading": b["prev"],
            "current_reading": b["curr"],
            "units": b["units"],
            "breakdown": {
                "slab_charges": calc["lines"],
                "energy_charge": calc["energy_charge"],
                "fixed_charge": calc["fixed_charge"],
                "duty": calc["duty"],
                "other_charges": 0.0,
                "rebate": 0.0
            },
            "calculated_total": calc["total"],
            "actual_total": b["actual"],
            "tariff_snapshot": {
                "name": tariff.get("name"),
                "distributor": tariff.get("distributor"),
                "slabs": tariff.get("slabs"),
                "fixed_charge": tariff.get("fixed_charge"),
                "duty_percent": tariff.get("duty_percent")
            },
            "source": "manual",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })

    # 5. Create appliances
    appliances = [
        {"name": "Split Air Conditioner (1.5 Ton)", "watts": 1500, "hours_per_day": 7, "days_per_month": 30, "quantity": 1, "monthly_kwh": 315.0, "estimated_cost": 2677.5},
        {"name": "Double Door Refrigerator", "watts": 220, "hours_per_day": 24, "days_per_month": 30, "quantity": 1, "monthly_kwh": 158.4, "estimated_cost": 1346.4},
        {"name": "Ceiling Fans (BLDC)", "watts": 30, "hours_per_day": 12, "days_per_month": 30, "quantity": 3, "monthly_kwh": 32.4, "estimated_cost": 275.4},
        {"name": "LED Bulbs", "watts": 9, "hours_per_day": 6, "days_per_month": 30, "quantity": 6, "monthly_kwh": 9.72, "estimated_cost": 82.62},
        {"name": "Water Geyser (Instant)", "watts": 3000, "hours_per_day": 0.5, "days_per_month": 30, "quantity": 1, "monthly_kwh": 45.0, "estimated_cost": 382.5}
    ]

    for a in appliances:
        a["user_id"] = user_id
        a["created_at"] = datetime.now(timezone.utc)
        db.appliances.insert_one(a)

    # 6. Create sample alerts
    alerts = [
        {
            "user_id": user_id,
            "type": "high_usage",
            "title": "High Consumption Alert",
            "message": "June 2026 consumption (230 units) exceeded your limit of 220 units.",
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        },
        {
            "user_id": user_id,
            "type": "spike",
            "title": "Usage Increase",
            "message": "Usage increased by 16.7% compared to April (180 → 210 units).",
            "is_read": True,
            "created_at": datetime.now(timezone.utc)
        }
    ]
    for alt in alerts:
        db.alerts.insert_one(alt)

    print("\n[+] Successfully seeded demo account:")
    print(f"   Email:    {demo_email}")
    print(f"   Password: password123")
    print(f"   Bills:    6 months (2026-01 to 2026-06)")
    print(f"   Appliances: 5 tracked appliances\n")

if __name__ == "__main__":
    seed_demo_data()
