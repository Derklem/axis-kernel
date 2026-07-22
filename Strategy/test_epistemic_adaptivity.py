import os
import sys
import json

# Add project roots to path
sys.path.append(r"d:\infinite")
sys.path.append(r"d:\infinite\Infinity\Strategy")

from multi_objective_solver import MultiObjectiveSolver

def test_epistemic_adaptivity():
    contract_path = r"D:\Infinite\Infinity\Strategy\Compiler\mission_contract.v1.json"
    solver = MultiObjectiveSolver(contract_path)
    
    # Mock proposal (legacy cleanup)
    proposal = {
        "proposal_id": "TEST-001",
        "origin_layer": "warehouse",
        "proposed_change": {
            "artifact_type": "legacy_cleanup",
            "action": "purge",
            "target_path": "d:\\infinite\\Warehouse\\Lab\\old_artifact.py",
            "delta": {"target": "old_artifact.py"}
        },
        "evaluation": {
            "expected_delta": 0.5,
            "prediction_conf": 0.8,
            "behavioral_impact_score": 0.0,
            "coupling_count": 0,
            "horizon_violation": False,
            "structural_confidence": 1.0,
            "provenance_hash": "mock_hash"
        }
    }
    
    state = {"posture": "FULL_AGENCY"}
    metrics = {"mttr_p95_24h": 180, "stability_volatility": 0.0}
    history = []
    
    print("--- EVALUATION WITH ZERO PRESSURE ---")
    res0 = solver.evaluate_proposal(proposal, state, metrics, history, epistemic_pressure=0.0)
    print(f"NMV: {res0['net_mission_value']}, Valuable: {res0['is_valuable']}")
    
    print("\n--- EVALUATION WITH HIGH PRESSURE (1200) ---")
    res1200 = solver.evaluate_proposal(proposal, state, metrics, history, epistemic_pressure=1200.0)
    print(f"NMV: {res1200['net_mission_value']}, Valuable: {res1200['is_valuable']}")
    print(f"Penalty Change: {res1200['semantic_penalty'] - res0['semantic_penalty']}")

    print("\n--- EVALUATION WITH EXTREME PRESSURE (2100) - STRUCTURAL REVISION ---")
    struct_proposal = proposal.copy()
    struct_proposal["proposed_change"]["artifact_type"] = "structural_revision"
    res2100 = solver.evaluate_proposal(struct_proposal, state, metrics, history, epistemic_pressure=2100.0)
    print(f"Rejection Reason: {res2100.get('rejection_reason')}")

if __name__ == "__main__":
    test_epistemic_adaptivity()
