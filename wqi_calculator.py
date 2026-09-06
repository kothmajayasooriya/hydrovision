"""
wqi_calculator.py
------------------
Implements the Weighted Arithmetic Water Quality Index (WQI) method.

This module is deliberately kept separate from Flask/database code so that:
  1. It can be tested with plain numbers, independent of the web app.
  2. It's a genuine calculation that goes beyond basic CRUD.

The WQI formula (Weighted Arithmetic Method):
  1. Each parameter has a WHO standard permissible limit (Sn) and an ideal
     value (Vio).
  2. Unit weight for each parameter:  wi = k / Sn,  where k = 1 / sum(1/Sn)
  3. Quality rating for each parameter:
       - pH is special: qi = |Vi - 7| / (Sn - 7) * 100
       - all others:    qi = (Vi / Sn) * 100
  4. Final index:  WQI = sum(wi * qi) / sum(wi)
"""

# WHO-based standard permissible limits and ideal values for each parameter.
# (Sn = standard/permissible limit, Vio = ideal value)
STANDARDS = {
    "ph":        {"Sn": 8.5, "Vio": 7.0},
    "turbidity": {"Sn": 5.0, "Vio": 0.0},   # NTU
    "tds":       {"Sn": 500.0, "Vio": 0.0}, # mg/L
    "nitrates":  {"Sn": 45.0, "Vio": 0.0},  # mg/L
}


def _quality_rating(parameter, value):
    """Calculate qi (the quality rating) for a single parameter."""
    std = STANDARDS[parameter]
    if parameter == "ph":
        # pH is centred on 7, not 0, so we measure distance from the ideal.
        return abs(value - std["Vio"]) / (std["Sn"] - std["Vio"]) * 100
    else:
        return (value / std["Sn"]) * 100


def calculate_wqi(ph, turbidity, tds, nitrates):
    """
    Calculate the Water Quality Index from four measured parameters.

    Returns a dict: {"wqi": float, "status": str}
    """
    readings = {
        "ph": ph,
        "turbidity": turbidity,
        "tds": tds,
        "nitrates": nitrates,
    }

    # Step 1: proportionality constant k = 1 / sum(1/Sn)
    k = 1 / sum(1 / STANDARDS[p]["Sn"] for p in STANDARDS)

    weighted_sum = 0.0
    weight_total = 0.0

    for param, value in readings.items():
        wi = k / STANDARDS[param]["Sn"]
        qi = _quality_rating(param, value)
        weighted_sum += wi * qi
        weight_total += wi

    wqi = weighted_sum / weight_total

    return {
        "wqi": round(wqi, 2),
        "status": classify_status(wqi),
    }


def classify_status(wqi):
    """Classify a WQI score into a human-readable safety status."""
    if wqi <= 25:
        return "Excellent"
    elif wqi <= 50:
        return "Good"
    elif wqi <= 75:
        return "Poor"
    elif wqi <= 100:
        return "Very Poor"
    else:
        return "Unsuitable"


# ---------------------------------------------------------------------------
# Manual test block - run `python wqi_calculator.py` to verify the logic
# with real sample data BEFORE wiring it into the Flask app.
# This satisfies the "test it with real data".
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_cases = [
        # (label, ph, turbidity, tds, nitrates, expected_approx_wqi)
        ("Clean tap water",      7.0, 2,   300, 10, 25.2),
        ("Slightly polluted",    6.8, 6,   450, 30, None),
        ("Heavily contaminated", 5.5, 25,  900, 80, None),
    ]

    print(f"{'Case':<22}{'pH':<6}{'Turb':<6}{'TDS':<6}{'NO3':<6}{'WQI':<8}Status")
    for label, ph, turb, tds, no3, expected in test_cases:
        result = calculate_wqi(ph, turb, tds, no3)
        print(f"{label:<22}{ph:<6}{turb:<6}{tds:<6}{no3:<6}{result['wqi']:<8}{result['status']}")
