"""
Slab-wise electricity bill calculation engine.
Calculates energy charges, line-by-line slab breakdowns, fixed charges, duty, and totals.
"""

def calculate_bill(units, tariff, rebate=0.0, other_charges=0.0):
    """
    Calculate electricity bill according to slab rules.
    
    Formula:
    Energy Charge = Sum(slab_units * slab_rate)
    Duty = (Energy Charge + Fixed Charge) * (Duty % / 100)
    Total = Energy Charge + Fixed Charge + Duty + Other Charges - Rebate
    """
    units = float(units) if units is not None else 0.0
    rebate = float(rebate) if rebate is not None else 0.0
    other_charges = float(other_charges) if other_charges is not None else float(tariff.get("other_charges", 0.0))
    fixed_charge = float(tariff.get("fixed_charge", 0.0))
    duty_percent = float(tariff.get("duty_percent", 0.0))
    
    remaining = max(0.0, units)
    energy_charge = 0.0
    lines = []
    
    slabs = tariff.get("slabs", [])
    
    for s in slabs:
        s_from = float(s.get("from", 0))
        s_to = float(s["to"]) if s.get("to") is not None else None
        rate = float(s.get("rate", 0))
        
        if s_to is not None:
            if s_from == 0:
                cap = s_to
            else:
                cap = (s_to - s_from + 1)
        else:
            cap = float("inf")
            
        used = min(remaining, cap)
        if used <= 0:
            if units == 0 and len(lines) == 0:
                lines.append({
                    "range": f"{int(s_from)}-{int(s_to) if s_to is not None else 'Above'}",
                    "units": 0,
                    "rate": rate,
                    "amount": 0.0
                })
            break
            
        amt = round(used * rate, 2)
        lines.append({
            "range": f"{int(s_from)}-{int(s_to) if s_to is not None else 'Above'}",
            "units": round(used, 2),
            "rate": rate,
            "amount": amt
        })
        energy_charge += amt
        remaining -= used
        
    energy_charge = round(energy_charge, 2)
    duty = round((energy_charge + fixed_charge) * duty_percent / 100.0, 2)
    total = round(energy_charge + fixed_charge + duty + other_charges - rebate, 2)
    
    # Calculate effective average cost per unit
    avg_cost_per_unit = round(total / units, 2) if units > 0 else 0.0
    
    # Identify which slab the consumption landed in and distance to next slab
    active_slab_info = _get_slab_insight(units, slabs)
    
    return {
        "units": units,
        "lines": lines,
        "energy_charge": energy_charge,
        "fixed_charge": fixed_charge,
        "duty_percent": duty_percent,
        "duty": duty,
        "other_charges": other_charges,
        "rebate": rebate,
        "total": max(0.0, total),
        "avg_cost_per_unit": avg_cost_per_unit,
        "slab_insight": active_slab_info
    }

def _get_slab_insight(units, slabs):
    for i, s in enumerate(slabs):
        s_from = float(s.get("from", 0))
        s_to = float(s["to"]) if s.get("to") is not None else None
        
        if s_to is None:
            return {
                "current_slab_index": i + 1,
                "current_slab_range": f"{int(s_from)}+",
                "is_highest_slab": True,
                "units_to_next_slab": 0,
                "warning": "You are in the highest tariff slab."
            }
            
        if s_from <= units <= s_to:
            units_left = round(s_to - units, 2)
            next_slab = slabs[i+1] if i + 1 < len(slabs) else None
            next_rate = next_slab.get("rate") if next_slab else None
            return {
                "current_slab_index": i + 1,
                "current_slab_range": f"{int(s_from)}-{int(s_to)}",
                "is_highest_slab": False,
                "units_to_next_slab": units_left,
                "next_slab_rate": next_rate,
                "warning": f"Only {units_left} units remaining before jumping to ₹{next_rate}/unit slab." if units_left <= 25 else None
            }
            
    return {
        "current_slab_index": 1,
        "current_slab_range": "0-100",
        "is_highest_slab": False,
        "units_to_next_slab": 100 - units if units <= 100 else 0,
        "warning": None
    }
