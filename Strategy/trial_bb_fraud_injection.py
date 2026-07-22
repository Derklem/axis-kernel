import json
import os
import hashlib
import sys

# Setup paths
STRATEGY_DIR = r"D:\Infinite\Infinity\Strategy"
sys.path.append(STRATEGY_DIR)
from multi_objective_solver import MultiObjectiveSolver

def compute_prov_hash(eval_block, metrics, ledger):
    # Simulation of Engine Centralized Factory Logic (Fail-Closed)
    target = eval_block.get("target_path", "explicit_checkpoint.json")
    health_registry = ledger.get("cluster_calibration_health", {})
    
    if target not in health_registry:
        eval_block["provenance_error"] = "missing_shadow_ledger_health"
        eval_block["structural_confidence"] = None
        eval_block["quarantine"] = True
    else:
        health = health_registry[target]
        eval_block["structural_confidence"] = health.get("structural_confidence", 1.0)
        eval_block["quarantine"] = health.get("quarantine", False)
    
    inputs = {
        "behavioral_impact": eval_block.get("behavioral_impact_score", 0.0),
        "coupling_count": eval_block.get("coupling_count", 0),
        "structural_confidence": eval_block.get("structural_confidence"), # None on error
        "horizon_violation": eval_block.get("horizon_violation", False),
        "sensor_integrity": eval_block.get("sensor_integrity_confidence", 1.0),
        "metrics_ts": metrics.get("timestamp_utc", "unknown"),
        "ledger_cycle": ledger.get("cycle_count", 0)
    }
    # Handling None in JSON for hashing
    payload = json.dumps(inputs, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()

def run_trials():
    print("=== Phase 36: Final Fail-Closed Provenance Trials ===")
    
    # Setup Hardened Ledger (Missing Target Health)
    shadow_ledger = {
        "cycle_count": 200,
        "calibration_ledger_integrity": {"status": "valid", "continuity_status": "intact"},
        "cluster_calibration_health": {
            # "explicit_checkpoint.json" is MISSING
            "other_file.json": {"structural_confidence": 1.0}
        },
        "forensic_archival_hash": "final_archival_hash_36"
    }
    
    mission_contract = os.path.join(STRATEGY_DIR, r"Compiler\mission_contract.v1.json")
    solver = MultiObjectiveSolver(mission_contract)
    metrics = {"stability_volatility": 0.0, "timestamp_utc": "2026-04-24T18:00:00Z"}
    state = {"metrics_health": "healthy"}

    # --- TRIAL DD: MISSING HEALTH (Hard Fail) ---
    print("\n--- Trial DD: Missing Health (Fail-Closed) ---")
    eval_orphan = { 
        "meta_mutation_eligible": True, 
        "target_path": "explicit_checkpoint.json",
        "behavioral_impact_score": 0.0,
        "coupling_count": 0,
        "horizon_violation": False,
        "sensor_integrity_confidence": 1.0
    }
    
    # Factory Sealing
    eval_orphan["provenance_hash"] = compute_prov_hash(eval_orphan, metrics, shadow_ledger)
    
    proposal = {
        "schema": "axis.strategy_proposal.v1",
        "proposed_change": { "artifact_type": "structural_revision", "target_path": "explicit_checkpoint.json" },
        "evaluation": eval_orphan
    }
    
    arb = solver.evaluate_proposal(proposal, state, metrics, [], shadow_ledger)
    print(f"Result: {arb.get('rejection_reason')}")
    print(f"Ancestry: {arb.get('governance_ancestry')}")
    
    if arb.get('rejection_reason') == "interpretation_fraud:missing_shadow_ledger_health":
        print("SUCCESS: Solver rejected orphan cluster mutation. Fail-closed confirmed.")
    else:
        print("FAILURE: Solver allowed mutation without health truth.")

if __name__ == "__main__":
    run_trials()
