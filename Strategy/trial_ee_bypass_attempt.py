import json
import os
import hashlib
import sys

# Setup paths
STRATEGY_DIR = r"D:\Infinite\Infinity\Strategy"
sys.path.append(STRATEGY_DIR)
from multi_objective_solver import MultiObjectiveSolver

def compute_adversarial_bypass_hash(eval_block, metrics, ledger):
    # This simulates an attacker exploiting the OLD fallback logic
    # They assume that since the target is missing, the solver will use 1.0
    inputs = {
        "behavioral_impact": eval_block.get("behavioral_impact_score", 0.0),
        "coupling_count": eval_block.get("coupling_count", 0),
        "structural_confidence": 1.0, # Attacker assumes solver fallback is 1.0
        "horizon_violation": eval_block.get("horizon_violation", False),
        "sensor_integrity": eval_block.get("sensor_integrity_confidence", 1.0),
        "metrics_ts": metrics.get("timestamp_utc", "unknown"),
        "ledger_cycle": ledger.get("cycle_count", 0)
    }
    return hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()

def run_trial_ee():
    print("=== Trial EE: Direct Solver Bypass Attempt ===")
    
    # 1. Setup Hardened Ledger (Missing Target Health)
    shadow_ledger = {
        "cycle_count": 250,
        "calibration_ledger_integrity": {"status": "valid", "continuity_status": "intact"},
        "cluster_calibration_health": {
            # "explicit_checkpoint.json" is MISSING
            "known_variable.json": {"structural_confidence": 1.0}
        },
        "forensic_archival_hash": "ee_archival_hash"
    }
    
    # 2. Construct Bypass Proposal (Lying about trust AND hash)
    metrics = {"stability_volatility": 0.0, "timestamp_utc": "2026-04-24T18:00:00Z"}
    
    eval_bypass = { 
        "meta_mutation_eligible": True, 
        "structural_confidence": 1.0, # FRAUD
        "behavioral_impact_score": 0.0,
        "coupling_count": 0,
        "horizon_violation": False,
        "sensor_integrity_confidence": 1.0
        # NOTE: provenance_error is OMITTED to simulate bypass
    }
    
    # Attacker computes hash based on expected fallback (1.0)
    eval_bypass["provenance_hash"] = compute_adversarial_bypass_hash(eval_bypass, metrics, shadow_ledger)
    
    proposal = {
        "schema": "axis.strategy_proposal.v1",
        "proposed_change": { "artifact_type": "structural_revision", "target_path": "explicit_checkpoint.json" },
        "evaluation": eval_bypass
    }
    
    # 3. Solver Challenge
    mission_contract = os.path.join(STRATEGY_DIR, r"Compiler\mission_contract.v1.json")
    solver = MultiObjectiveSolver(mission_contract)
    state = {"metrics_health": "healthy"}
    
    print("Challenging Solver with Adversarial Bypass...")
    arb = solver.evaluate_proposal(proposal, state, metrics, [], shadow_ledger)
    
    print(f"Result: {arb.get('rejection_reason')}")
    print(f"Ancestry: {arb.get('governance_ancestry')}")
    
    if arb.get('rejection_reason') == "interpretation_fraud:missing_shadow_ledger_health":
        print("\nSUCCESS: Solver independently detected missing health truth. Bypass prevented.")
    else:
        print("\nFAILURE: Solver fell back to default trust and allowed the bypass!")

if __name__ == "__main__":
    run_trial_ee()
