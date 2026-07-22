import sys
import os
import json

# Add strategy dir to path
sys.path.append(r"d:\infinite\Infinity\Strategy")
from strategy_engine import StrategyEngine

def test_throttling():
    print("--- Phase 53 Throttling Verification ---")
    engine = StrategyEngine()
    
    # Trigger Audit to sync state
    engine._audit_semantic_proposals(engine.shadow_ledger)
    
    # Helper to evaluate
    def eval_artifact(name, ledger):
        mock_p = {
            "proposed_change": {
                "artifact_type": "generic_optimization",
                "target_path": f"Warehouse/{name}",
                "delta": {"update": 1}
            },
            "evaluation": {
                "prediction_conf": 1.0,
                "expected_delta": 0.05,
                "structural_confidence": 1.0,
                "sensor_integrity_confidence": 1.0
            }
        }
        res = engine.solver.evaluate_proposal(mock_p, {"posture": "FULL_AGENCY"}, {"stability_index": 100}, [], shadow_ledger=ledger, epistemic_pressure=100.0)
        return res

    print("\nCase 1: explicit_checkpoint.json (High Priority Stale: 5.94)")
    res1 = eval_artifact("explicit_checkpoint.json", engine.shadow_ledger)
    
    print("\nCase 2: strategy_engine.py (Medium Priority Stale: 1.98)")
    res2 = eval_artifact("strategy_engine.py", engine.shadow_ledger)

    print("\n--- Results Analysis ---")
    # Case 1 should have 'stale_critical_throttle' in output (we check it via stdout in real run)
    # But here we can check the utility drop.
    # Base utility was -188.70 in Phase 52.
    # With throttle -20.0, it should be -208.70.
    
    u1 = res1.get("action_utility")
    u2 = res2.get("action_utility")
    
    print(f"Utility (High Priority Stale): {u1:.2f}")
    print(f"Utility (Medium Priority Stale): {u2:.2f}")

    if u1 < -200.0:
        print("\nSUCCESS: Stale Criticality Throttling confirmed for High Priority.")
    else:
        print("\nFAILURE: Throttling not applied or insufficient.")

if __name__ == "__main__":
    test_throttling()
