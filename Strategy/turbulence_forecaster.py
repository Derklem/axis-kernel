import json
import os
import time

def analyze_drift(outcomes_path):
    """
    Calculates rolling Mean Absolute Error (MAE) of predictions.
    Returns drift score [0.0 - 1.0] and raw errors.
    """
    if not os.path.exists(outcomes_path):
        return 0.0, []

    errors = []
    try:
        with open(outcomes_path, "r") as f:
            lines = f.readlines()[-20:] # Last 20 outcomes
            for line in lines:
                if not line.strip(): continue
                data = json.loads(line)
                pred = data.get("predicted", {})
                actual = data.get("actual", {})
                
                # Combine v1, v2, v3 errors
                p_score = (pred.get("v1_variance", 0) + pred.get("v2_velocity", 0) + pred.get("v3_backlog", 0)) / 3.0
                a_score = (min(1.0, actual.get("v1_variance", 0)/10.0) + min(1.0, actual.get("v2_velocity", 0)/5.0) + min(1.0, actual.get("v3_backlog", 0))) / 3.0
                errors.append(abs(p_score - a_score))
    except: pass

    if not errors:
        return 0.0, []

    mae = sum(errors) / len(errors)
    # Drift is normalized MAE. 0.3 MAE is considered high drift.
    drift_score = min(1.0, mae / 0.3)
    return round(drift_score, 3), errors

def calculate_turbulence_score(models, drift_score):
    """
    Combines current instability with historical drift.
    """
    # Current Instability (normalized)
    v1_n = min(1.0, models.get("v1_variance", 0) / 10.0)
    v2_n = min(1.0, models.get("v2_velocity", 0) / 5.0)
    v3_n = min(1.0, models.get("v3_backlog", 0))
    instability = (v1_n + v2_n + v3_n) / 3.0
    
    # Turbulence = 60% Current Instability + 40% Historical Drift
    score = (instability * 0.6) + (drift_score * 0.4)
    return round(min(1.0, score), 3)

if __name__ == "__main__":
    # Test stub
    m = {"v1_variance": 5.0, "v2_velocity": 2.0, "v3_backlog": 0.5}
    print(f"Turbulence Score: {calculate_turbulence_score(m, 0.2)}")
