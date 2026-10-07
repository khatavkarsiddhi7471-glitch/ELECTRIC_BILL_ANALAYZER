"""
Prediction service for electricity consumption and bill forecasting.
Uses 3-Month Moving Average for 3-5 bills, and Ordinary Least Squares (OLS) Linear Regression with confidence bounds for 6+ bills.
"""

from backend.services.calculator import calculate_bill

def predict_next_bill(bills, tariff):
    """
    Predict next month's units and calculated cost.
    bills: list of bill dicts sorted chronologically ascending
    tariff: active tariff dictionary
    """
    n = len(bills)
    
    if n < 3:
        return {
            "status": "insufficient_data",
            "message": "Add at least 3 months of bills for accurate prediction.",
            "data_points_count": n,
            "predicted_units": None,
            "predicted_amount": None,
            "method": None,
            "confidence_range": None
        }
        
    units_history = [float(b.get("units", 0)) for b in bills]
    
    if n < 6:
        # 3 to 5 data points -> 3-Month Moving Average
        last_3 = units_history[-3:]
        predicted_units = round(sum(last_3) / len(last_3), 1)
        method = "3-Month Moving Average"
        confidence_percent = 12.0
    else:
        # >= 6 data points -> OLS Linear Regression
        x = list(range(n))
        y = units_history
        
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi ** 2 for xi in x)
        
        denom = (n * sum_x2 - sum_x ** 2)
        if denom != 0:
            slope = (n * sum_xy - sum_x * sum_y) / denom
            intercept = (sum_y - slope * sum_x) / n
            next_x = n
            pred_raw = slope * next_x + intercept
            predicted_units = round(max(0.0, float(pred_raw)), 1)
        else:
            predicted_units = round(sum(units_history[-3:]) / 3.0, 1)
            
        method = "Linear Regression (Trend Analysis)"
        confidence_percent = 8.0

    # Pass predicted units through standard slab calculator
    calc_result = calculate_bill(predicted_units, tariff)
    predicted_amount = calc_result["total"]
    
    # Calculate confidence interval
    lower_units = max(0.0, round(predicted_units * (1.0 - confidence_percent / 100.0), 1))
    upper_units = round(predicted_units * (1.0 + confidence_percent / 100.0), 1)
    
    lower_amount = calculate_bill(lower_units, tariff)["total"]
    upper_amount = calculate_bill(upper_units, tariff)["total"]
    
    return {
        "status": "success",
        "predicted_units": predicted_units,
        "predicted_amount": predicted_amount,
        "method": method,
        "data_points_count": n,
        "confidence_range": {
            "units_range": [lower_units, upper_units],
            "amount_range": [lower_amount, upper_amount],
            "margin_percent": confidence_percent
        },
        "breakdown": calc_result["lines"],
        "energy_charge": calc_result["energy_charge"],
        "fixed_charge": calc_result["fixed_charge"],
        "duty": calc_result["duty"],
        "slab_insight": calc_result["slab_insight"]
    }
