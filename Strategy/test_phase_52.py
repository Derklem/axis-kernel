import sys
import os
import json

# Add strategy dir to path
sys.path.append(r"d:\infinite\Infinity\Strategy")
from strategy_engine import StrategyEngine

def test_credit_decay():
    print("--- Phase 52 Credit Decay Verification ---")
    engine = StrategyEngine()
    
    # Trigger Audit to sync state and emit witnesses
    engine._audit_semantic_proposals(engine.shadow_ledger)
    
    state = engine.shadow_ledger.get("semantic_epistemic_state", {})
    synergy_index = state.get("synergy_index", 0.0)
    print(f"Global Synergy Index: {synergy_index}")

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
        return res.get("action_utility")

    # 1. Evaluate with STALE credit
    print("\nCase: explicit_checkpoint.json (STALE CREDIT)")
    u_stale = eval_artifact("explicit_checkpoint.json", engine.shadow_ledger)
    
    # 2. Compare with what it WOULD have been if it were verified (0.99)
    # We'll mock a verified ledger
    verified_ledger = json.loads(json.dumps(engine.shadow_ledger))
    for edge in verified_ledger["semantic_epistemic_state"]["synergy_edges"]:
        if "explicit_checkpoint.json" in edge["artifacts"]:
            edge["evidence_class"] = "counterfactual_verified"
            edge["synergy_score"] = 0.99
            
    u_verified = eval_artifact("explicit_checkpoint.json", verified_ledger)
    
    print(f"\nUtility (Stale): {u_stale:.2f}")
    print(f"Utility (Verified): {u_verified:.2f}")
    
    withheld = round(u_verified - u_stale, 2)
    print(f"Credit Withheld: {withheld}")

    if withheld > 20.0:
        print("\nSUCCESS: Phase 52 Credit Decay verified.")
        print("Stale credit utility significantly lower than verified utility.")
    else:
        print("\nFAILURE: Credit decay logic is insufficient.")

if __name__ == "__main__":
    test_credit_decay()
