"""
Rule-based energy savings and advisory engine.
Analyzes consumption patterns, top appliances, slab thresholds, and suggests tailored savings tips.
"""

def generate_energy_tips(bills, appliances, active_tariff):
    """
    Generate personalised and general energy saving tips.
    """
    tips = []
    
    # 1. Base / Universal tips
    tips.append({
        "id": "tip-led",
        "category": "Lighting",
        "title": "Upgrade to 9W LED Bulbs",
        "tip": "Replace traditional 60W incandescent/CFL bulbs with high-efficiency 9W LEDs. Operates at 85% less energy.",
        "estimated_monthly_savings_inr": 180,
        "estimated_kwh_savings": 22,
        "priority": "Medium",
        "tag": "Quick Win"
    })
    
    tips.append({
        "id": "tip-standby",
        "category": "Behavioral",
        "title": "Eliminate Phantom Standby Power",
        "tip": "Smart TVs, microwave ovens, gaming consoles, and set-top boxes draw standby power continuously. Switch off power strips when not in use.",
        "estimated_monthly_savings_inr": 120,
        "estimated_kwh_savings": 15,
        "priority": "Low",
        "tag": "Zero Cost"
    })
    
    # 2. Appliance-driven personalized tips
    if appliances:
        sorted_apps = sorted(appliances, key=lambda x: x.get("monthly_kwh", 0), reverse=True)
        top_app = sorted_apps[0]
        top_name = top_app.get("name", "").lower()
        top_kwh = top_app.get("monthly_kwh", 0)
        
        if "ac" in top_name or "air conditioner" in top_name or "air-conditioner" in top_name:
            tips.insert(0, {
                "id": "tip-ac-optimal",
                "category": "Cooling",
                "title": f"Optimize AC Temperature (24°C - 26°C)",
                "tip": f"Your AC accounts for {top_kwh:.1f} kWh/month. Increasing thermostat from 18°C to 24°C reduces AC power draw by 6% per degree (up to 30% total savings).",
                "estimated_monthly_savings_inr": round(top_app.get("estimated_cost", 0) * 0.24, 0),
                "estimated_kwh_savings": round(top_kwh * 0.24, 1),
                "priority": "High",
                "tag": "Top Consumer"
            })
            tips.append({
                "id": "tip-ac-filter",
                "category": "Cooling",
                "title": "Clean AC Filters Bi-Weekly",
                "tip": "Clogged filters force the compressor to work 15% harder to circulate air. Routine cleaning saves power and prolongs compressor life.",
                "estimated_monthly_savings_inr": round(top_app.get("estimated_cost", 0) * 0.08, 0),
                "estimated_kwh_savings": round(top_kwh * 0.08, 1),
                "priority": "Medium",
                "tag": "Maintenance"
            })
            
        if "geyser" in top_name or "water heater" in top_name:
            tips.insert(0, {
                "id": "tip-geyser-timer",
                "category": "Heating",
                "title": "Set Geyser Timer to 15 Minutes",
                "tip": "Water heaters consume 2000W-3000W. Switching off 15 mins after heating avoids standby re-heating cycles throughout the day.",
                "estimated_monthly_savings_inr": round(top_app.get("estimated_cost", 0) * 0.20, 0),
                "estimated_kwh_savings": round(top_kwh * 0.20, 1),
                "priority": "High",
                "tag": "High Impact"
            })
            
        if "fridge" in top_name or "refrigerator" in top_name:
            tips.append({
                "id": "tip-fridge-coil",
                "category": "Refrigeration",
                "title": "Optimize Refrigerator Airflow & Temperature",
                "tip": "Keep refrigerator 3 inches from wall and set temperature to Medium (3-4°C). Avoid keeping hot food inside directly.",
                "estimated_monthly_savings_inr": 90,
                "estimated_kwh_savings": 12,
                "priority": "Medium",
                "tag": "Best Practice"
            })

    # 3. Bill History & Slab-driven personalized tips
    if bills and len(bills) >= 1:
        latest_bill = bills[-1]
        latest_units = float(latest_bill.get("units", 0))
        slabs = active_tariff.get("slabs", [])
        
        # Check slab boundary warning
        for s in slabs:
            s_to = s.get("to")
            if s_to and (s_to - 15) <= latest_units <= s_to:
                diff = s_to - latest_units
                tips.insert(0, {
                    "id": "tip-slab-leap",
                    "category": "Tariff Optimization",
                    "title": f"Stay in Lower Slab: Cut {diff:.0f} Units",
                    "tip": f"Your current usage ({latest_units:.0f} units) is within {diff:.0f} units of crossing into the higher rate slab. Reducing small usage avoids high marginal rates.",
                    "estimated_monthly_savings_inr": 250,
                    "estimated_kwh_savings": diff,
                    "priority": "Critical",
                    "tag": "Slab Alert"
                })
                break
                
        # Check MoM spike
        if len(bills) >= 2:
            prev_bill = bills[-2]
            prev_units = float(prev_bill.get("units", 0))
            if prev_units > 0:
                pct_change = ((latest_units - prev_units) / prev_units) * 100.0
                if pct_change >= 20.0:
                    tips.insert(0, {
                        "id": "tip-spike-audit",
                        "category": "Consumption Alert",
                        "title": f"Usage Spike Detected (+{pct_change:.1f}%)",
                        "tip": f"Your consumption jumped {pct_change:.1f}% compared to {prev_bill.get('month', 'last month')}. Check for faulty wiring, new high-wattage appliances, or continuous AC/geyser running.",
                        "estimated_monthly_savings_inr": 350,
                        "estimated_kwh_savings": round(latest_units - prev_units, 1),
                        "priority": "Critical",
                        "tag": "Spike Warning"
                    })
                    
    return tips
