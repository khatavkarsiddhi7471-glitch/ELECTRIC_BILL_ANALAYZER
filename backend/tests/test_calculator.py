import pytest
from backend.services.calculator import calculate_bill

@pytest.fixture
def standard_tariff():
    return {
        "name": "MSEDCL Residential Test",
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

def test_prd_worked_example_150_units(standard_tariff):
    """
    Test PRD Worked Example:
    Units: 150
    Slab 0-100: 100 * 5 = 500
    Slab 101-300: 50 * 10 = 500
    Energy charge = 1000
    Fixed charge = 120
    Duty (16% of 1120) = 179.20
    Rebate = 0
    Total = 1299.20
    """
    result = calculate_bill(150, standard_tariff)
    assert result["energy_charge"] == 1000.00
    assert result["fixed_charge"] == 120.00
    assert result["duty"] == 179.20
    assert result["total"] == 1299.20
    assert len(result["lines"]) == 2
    assert result["lines"][0]["units"] == 100
    assert result["lines"][0]["amount"] == 500.00
    assert result["lines"][1]["units"] == 50
    assert result["lines"][1]["amount"] == 500.00

def test_zero_units(standard_tariff):
    result = calculate_bill(0, standard_tariff)
    assert result["energy_charge"] == 0.0
    assert result["fixed_charge"] == 120.0
    assert result["duty"] == 19.20  # 16% of 120
    assert result["total"] == 139.20

def test_boundary_100_units(standard_tariff):
    result = calculate_bill(100, standard_tariff)
    assert result["energy_charge"] == 500.00
    assert len(result["lines"]) == 1

def test_boundary_101_units(standard_tariff):
    result = calculate_bill(101, standard_tariff)
    assert result["energy_charge"] == 510.00  # 500 + 1*10
    assert len(result["lines"]) == 2

def test_boundary_300_units(standard_tariff):
    result = calculate_bill(300, standard_tariff)
    # 100 * 5 = 500, 200 * 10 = 2000 => 2500
    assert result["energy_charge"] == 2500.00

def test_boundary_301_units(standard_tariff):
    result = calculate_bill(301, standard_tariff)
    # 100 * 5 = 500, 200 * 10 = 2000, 1 * 14 = 14 => 2514
    assert result["energy_charge"] == 2514.00
    assert len(result["lines"]) == 3

def test_rebate_and_surcharges(standard_tariff):
    result = calculate_bill(100, standard_tariff, rebate=50.0, other_charges=25.0)
    # Energy: 500, Fixed: 120, Duty: (500+120)*0.16 = 99.20
    # Total: 500 + 120 + 99.20 + 25 - 50 = 694.20
    assert result["total"] == 694.20
