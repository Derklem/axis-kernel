from F8_1_Market_Dynamics_Engine import append_observation, append_resolution
import os
import json

MARKET_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_theory_market_v2.jsonl"
OBSERVATIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_observations.jsonl"
REJECTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_rejections.jsonl"
OVERRIDES_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_operational_overrides.jsonl"
REGISTRY_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\source_authority_registry.json"
PREDICTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_predictions.jsonl"
RESOLUTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_prediction_resolutions.jsonl"

def reset_env():
    for p in [MARKET_PATH, OBSERVATIONS_PATH, REJECTIONS_PATH, OVERRIDES_PATH, REGISTRY_PATH, PREDICTIONS_PATH, RESOLUTIONS_PATH]:
        if os.path.exists(p): os.remove(p)
    
    reg = {
        "sources": {
            "live log": {"allowed_groups": ["G1", "G2", "G3", "G4"], "trust_score": 1.0},
            "operator": {"allowed_groups": ["G1", "G2", "G3", "G4"], "trust_score": 1.0},
            "validator": {
                "allowed_groups": ["G1", "G2", "G3", "G4"],
                "trust_score": 1.0,
                "can_resolve": True
            }
        }
    }
    with open(REGISTRY_PATH, 'w') as f:
        json.dump(reg, f)
        
    import F8_Epistemic_Theory_Market_v2 as init
    init.initialize_market()

def test_f8_7():
    reset_env()
    print("=== Testing F8.7 Outcome Resolution ===")
    
    # Generate an initial prediction
    evt = append_observation({
        "theory_group_id": "G4",
        "supports_theory_id": "T4",
        "evidence_weight": 2.0,
        "reason": "Forecast creation",
        "is_drill": False,
        "source": "live log",
        "confirming_source": "validator",
        "provenance": {"type": "report_id", "ref": "R-100"},
        "confirming_provenance": {"type": "log_id", "ref": "L-100"},
        "forecast": {
            "claim": "Will decrease errors",
            "expected_metric": "error_rate",
            "baseline": 0.05,
            "target": 0.01,
            "direction": "decrease",
            "evaluation_after_days": 14,
            "success_condition": "error_rate <= 0.02"
        }
    })
    
    pred_id = None
    with open(PREDICTIONS_PATH, 'r') as f:
        for line in f:
            if line.strip():
                pred_id = json.loads(line)['prediction_id']
                break
                
    print(f"Generated Prediction: {pred_id}")
    
    print("\n1. Resolving with unregistered source (should fail)...")
    append_resolution({
        "prediction_id": pred_id,
        "resolution_source": "hacker",
        "observed_metric": "error_rate",
        "observed_value": 0.015,
        "success": True,
        "resolution_provenance": {"type": "report_id", "ref": "R-RES1"}
    })
    
    print("\n2. Resolving with registered source lacking can_resolve (should fail)...")
    append_resolution({
        "prediction_id": pred_id,
        "resolution_source": "operator",
        "observed_metric": "error_rate",
        "observed_value": 0.015,
        "success": True,
        "resolution_provenance": {"type": "report_id", "ref": "R-RES2"}
    })
    
    print("\n3. Resolving unknown prediction ID (should fail)...")
    append_resolution({
        "prediction_id": "PRED-UNKNOWN",
        "resolution_source": "validator",
        "observed_metric": "error_rate",
        "observed_value": 0.015,
        "success": True,
        "resolution_provenance": {"type": "report_id", "ref": "R-RES3"}
    })
    
    print("\n4. Valid resolution (should pass)...")
    append_resolution({
        "prediction_id": pred_id,
        "resolution_source": "validator",
        "observed_metric": "error_rate",
        "observed_value": 0.015,
        "success": True,
        "resolution_provenance": {"type": "report_id", "ref": "R-RES4"}
    })
    
    print("\n5. Duplicate resolution (should fail)...")
    append_resolution({
        "prediction_id": pred_id,
        "resolution_source": "validator",
        "observed_metric": "error_rate",
        "observed_value": 0.015,
        "success": True,
        "resolution_provenance": {"type": "report_id", "ref": "R-RES5"}
    })

    print("\nGenerating F8.4 Report...")
    import F8_4_Market_Observability as obs
    obs.generate_report()

if __name__ == "__main__":
    test_f8_7()
