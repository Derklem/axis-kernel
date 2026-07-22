from F8_1_Market_Dynamics_Engine import append_observation
import os

MARKET_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_theory_market_v2.jsonl"
OBSERVATIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_observations.jsonl"
REJECTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_rejections.jsonl"
OVERRIDES_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_operational_overrides.jsonl"
REGISTRY_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\source_authority_registry.json"
PREDICTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_predictions.jsonl"

def reset_env():
    for p in [MARKET_PATH, OBSERVATIONS_PATH, REJECTIONS_PATH, OVERRIDES_PATH, REGISTRY_PATH, PREDICTIONS_PATH]:
        if os.path.exists(p): os.remove(p)
    
    import json
    reg = {
        "sources": {
            "live log": {"allowed_groups": ["G1", "G2", "G3", "G4"], "trust_score": 1.0},
            "validator": {"allowed_groups": ["G1", "G2", "G3", "G4"], "trust_score": 1.0}
        }
    }
    with open(REGISTRY_PATH, 'w') as f:
        json.dump(reg, f)
        
    import F8_Epistemic_Theory_Market_v2 as init
    init.initialize_market()

def test_f8_6():
    reset_env()
    print("=== Testing F8.6 Predictive Accountability ===")
    
    # 1. Invalid high-impact event (missing forecast)
    print("\n1. Submitting high-impact event without forecast...")
    append_observation({
        "theory_group_id": "G4",
        "supports_theory_id": "T4",
        "evidence_weight": 2.0,
        "reason": "Missing forecast test",
        "is_drill": False,
        "source": "live log",
        "confirming_source": "validator",
        "provenance": {"type": "report_id", "ref": "R-100"},
        "confirming_provenance": {"type": "log_id", "ref": "L-100"}
    })
    
    # 2. Valid high-impact event (with forecast)
    print("\n2. Submitting high-impact event WITH forecast...")
    append_observation({
        "theory_group_id": "G4",
        "supports_theory_id": "T4",
        "evidence_weight": 2.0,
        "reason": "Forecast test",
        "is_drill": False,
        "source": "live log",
        "confirming_source": "validator",
        "provenance": {"type": "report_id", "ref": "R-101"},
        "confirming_provenance": {"type": "log_id", "ref": "L-101"},
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
    
    # 3. Valid low-impact event (no forecast required)
    print("\n3. Submitting low-impact event without forecast...")
    append_observation({
        "theory_group_id": "G4",
        "supports_theory_id": "T4",
        "evidence_weight": 1.0,
        "reason": "Low impact test",
        "is_drill": False,
        "source": "live log",
        "provenance": {"type": "report_id", "ref": "R-102"}
    })

    import F8_4_Market_Observability as obs
    obs.generate_report()

if __name__ == "__main__":
    test_f8_6()
