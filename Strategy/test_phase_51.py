import sys
import os
import json

# Add strategy dir to path
sys.path.append(r"d:\infinite\Infinity\Strategy")
from strategy_engine import StrategyEngine

def test_local_synergy():
    print("--- Phase 51 Local Synergy Verification ---")
    engine = StrategyEngine()
    
    # Verification Strategy: Run it twice.
    # Once with synergy edges, once without.
    
    def eval_with_ledger(name, ledger):
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

    print("\n--- Phase 51 Local Attribution Test ---")
    
    # 1. Clean Ledger (No Synergies)
    clean_ledger = json.loads(json.dumps(engine.shadow_ledger))
    clean_ledger["semantic_epistemic_state"]["synergy_edges"] = []
    clean_ledger["semantic_epistemic_state"]["synergy_index"] = 0.0
    
    # 2. Synergistic Ledger
    syn_ledger = json.loads(json.dumps(engine.shadow_ledger))
    syn_ledger["semantic_epistemic_state"] = {
        "synergy_index": 0.028,
        "synergy_edges": [
            {
                "edge_id": "SYN-TEST",
                "artifacts": ["explicit_checkpoint.json", "latent_competitor_g.json"],
                "synergy_score": 0.99,
                "evidence_class": "counterfactual_verified"
            }
        ]
    }
    
    # Test Sentinel
    u_base = eval_with_ledger("explicit_checkpoint.json", clean_ledger)
    u_syn = eval_with_ledger("explicit_checkpoint.json", syn_ledger)
    bonus_sentinel = round(u_syn - u_base, 2)
    
    # Test Unrelated
    u_base_un = eval_with_ledger("coordinated_executor.py", clean_ledger)
    u_syn_un = eval_with_ledger("coordinated_executor.py", syn_ledger)
    bonus_unrelated = round(u_syn_un - u_base_un, 2)
    
    print(f"Sentinel Bonus: {bonus_sentinel}")
    print(f"Unrelated Bonus: {bonus_unrelated}")
    
    if bonus_sentinel > 25.0 and bonus_unrelated < 1.0:
        print("\nSUCCESS: Phase 51 Local Synergy Attribution verified.")
        print("Verified Sentinel received full credit. Unrelated artifact received only ambient credit.")
    else:
        print("\nFAILURE: Credit assignment is not localized.")

if __name__ == "__main__":
    test_local_synergy()
