import pytest
import json
from backend.app import create_app
from backend.config import Config

class TestConfig(Config):
    TESTING = True
    DB_NAME = "electricity_analyzer_test"

@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.app_context():
        from backend.utils.db import get_db
        db = get_db()
        db.users.delete_many({"email": "tester@example.com"})
        db.bills.delete_many({})
        db.appliances.delete_many({})
    with app.test_client() as client:
        yield client

def test_full_auth_and_bill_flow(client):
    # 1. Register a test user
    reg_res = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "tester@example.com",
        "password": "Password123!",
        "distributor": "MSEDCL"
    })
    assert reg_res.status_code == 201
    reg_data = reg_res.get_json()
    assert reg_data["success"] is True
    token = reg_data["data"]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Profile (/me)
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.get_json()["data"]["email"] == "tester@example.com"

    # 3. Add a manual bill for 2026-01
    bill_res = client.post("/api/v1/bills", headers=headers, json={
        "month": "2026-01",
        "previous_reading": 1000,
        "current_reading": 1150,
        "actual_total": 1300
    })
    assert bill_res.status_code == 201
    bill_data = bill_res.get_json()["data"]
    assert bill_data["units"] == 150
    assert bill_data["calculated_total"] == 1299.20
    bill_id = bill_data["id"]

    # 4. Fetch Bill Detail
    detail_res = client.get(f"/api/v1/bills/{bill_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.get_json()["data"]["units"] == 150

    # 5. Check Summary Analytics
    sum_res = client.get("/api/v1/analytics/summary", headers=headers)
    assert sum_res.status_code == 200
    assert sum_res.get_json()["data"]["total_bills"] == 1
    assert sum_res.get_json()["data"]["latest_units"] == 150

    # 6. Add an Appliance
    app_res = client.post("/api/v1/appliances", headers=headers, json={
        "name": "Air Conditioner",
        "watts": 1500,
        "hours_per_day": 8,
        "days_per_month": 30,
        "quantity": 1
    })
    assert app_res.status_code == 201
    assert app_res.get_json()["data"]["monthly_kwh"] == 360.0  # (1500 * 8 * 30 * 1) / 1000

    # 7. Check Saving Tips Generation
    tips_res = client.get("/api/v1/tips", headers=headers)
    assert tips_res.status_code == 200
    tips = tips_res.get_json()["data"]["tips"]
    assert len(tips) > 0
    # AC tip should be generated since AC is top consumer
    ac_tips = [t for t in tips if "AC" in t["title"] or "Cooling" in t["category"]]
    assert len(ac_tips) > 0

    # 8. Stateless Calculator
    calc_res = client.post("/api/v1/bills/calculate", json={"units": 200})
    assert calc_res.status_code == 200
    assert calc_res.get_json()["data"]["total"] > 0
