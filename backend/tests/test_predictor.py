import pytest
from backend.services.predictor import predict_next_bill

@pytest.fixture
def test_tariff():
    return {
        "name": "Test Tariff",
        "slabs": [
            {"from": 0, "to": 100, "rate": 5.0},
            {"from": 101, "to": 300, "rate": 10.0},
            {"from": 301, "to": None, "rate": 14.0}
        ],
        "fixed_charge": 120.0,
        "duty_percent": 16.0,
        "other_charges": 0.0
    }

def test_insufficient_data_less_than_3_bills(test_tariff):
    bills = [
        {"month": "2026-01", "units": 150},
        {"month": "2026-02", "units": 160}
    ]
    res = predict_next_bill(bills, test_tariff)
    assert res["status"] == "insufficient_data"
    assert res["predicted_units"] is None

def test_moving_average_3_to_5_bills(test_tariff):
    bills = [
        {"month": "2026-01", "units": 100},
        {"month": "2026-02", "units": 150},
        {"month": "2026-03", "units": 200}
    ]
    res = predict_next_bill(bills, test_tariff)
    assert res["status"] == "success"
    assert res["predicted_units"] == 150.0  # (100+150+200)/3
    assert res["predicted_amount"] == 1299.20
    assert "Moving Average" in res["method"]

def test_linear_regression_6_or_more_bills(test_tariff):
    # Steady upward trend: 100, 110, 120, 130, 140, 150
    bills = [
        {"month": f"2026-0{i}", "units": 100 + (i - 1) * 10}
        for i in range(1, 7)
    ]
    res = predict_next_bill(bills, test_tariff)
    assert res["status"] == "success"
    # Expected next value is approx 160
    assert 158.0 <= res["predicted_units"] <= 162.0
    assert res["predicted_amount"] > 0
    assert "Linear Regression" in res["method"] or "Moving Average" in res["method"]
