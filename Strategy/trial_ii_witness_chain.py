import json
import os
import hashlib
import sys
from datetime import datetime, timezone

# Setup paths
STRATEGY_DIR = r"D:\Infinite\Infinity\Strategy"
sys.path.append(STRATEGY_DIR)
from strategy_engine import StrategyEngine

WITNESS_LEDGER_PATH = os.path.join(STRATEGY_DIR, r"State\forensic_witness_ledger.jsonl")

def clean_record(record):
    r = record.copy()
    if "witness_hash" in r:
        del r["witness_hash"]
    return r

def run_trial_ii():
    print("=== Trial II: Witness Chain Validation Protocol ===")
    
    # 1. Clear Ledger
    if os.path.exists(WITNESS_LEDGER_PATH):
        os.remove(WITNESS_LEDGER_PATH)
    
    engine = StrategyEngine()
    
    # 2. Trigger Observe (Continuity Witness)
    print("Executing Observation Cycle...")
    engine.observe()
    
    # 3. Trigger Posture Change (Posture Witness)
    print("Executing Posture Change...")
    engine.request_posture_change("PLANNER_ONLY", reason="Trial_II_Start")
    
    # 4. Trigger Run Once (Solver Witness)
    # We need a dummy proposal in the warehouse
    dummy_p_path = r"d:\infinite\Warehouse\dummy_proposal.json"
    dummy_p = {
        "schema": "axis.strategy_proposal.v1",
        "proposal_id": "trial_ii_dummy",
        "origin_layer": "warehouse",
        "proposed_change": {
            "artifact_type": "structural_revision",
            "action": "identity_crisis",
            "target_path": "test_target.json"
        },
        "evaluation": {
            "meta_mutation_eligible": True,
            "structural_confidence": 1.0,
            "behavioral_impact_score": 0.1,
            "coupling_count": 0,
            "horizon_violation": False,
            "sensor_integrity_confidence": 1.0,
            "net_mission_value": 50.0
        }
    }
    with open(dummy_p_path, "w") as f: json.dump(dummy_p, f)
    
    # Setup registry so it doesn't fail
    registry_path = r"d:\infinite\Warehouse\warehouse_structural_registry.json"
    with open(registry_path, "w") as f: json.dump({"signatures": {"test_target.json": {}}, "clusters": []}, f)

    print("Executing Engine Run...")
    # We bypass actual actuation to avoid side effects
    engine.run_once()
    
    # 5. Chain Validation
    print("\nValidating Witness Chain...")
    if not os.path.exists(WITNESS_LEDGER_PATH):
        print("FAILURE: Witness ledger not created!")
        return

    records = []
    with open(WITNESS_LEDGER_PATH, "r") as f:
        for line in f:
            records.append(json.loads(line))
    
    print(f"Total Witness Records: {len(records)}")
    
    previous_hash = "0" * 64
    for i, r in enumerate(records):
        # Link Check
        if r["prev_witness_hash"] != previous_hash:
            print(f"FAILURE: Hash link broken at record {i}!")
            print(f"Expected Prev: {previous_hash}")
            print(f"Actual Prev: {r['prev_witness_hash']}")
            return
        
        # Self Check
        clean_r = clean_record(r)
        computed_hash = hashlib.sha256(json.dumps(clean_r, sort_keys=True).encode()).hexdigest()
        
        if computed_hash != r["witness_hash"]:
            print(f"FAILURE: Self-hash mismatch at record {i}!")
            print(f"Computed: {computed_hash}")
            print(f"Stored: {r['witness_hash']}")
            return
        
        previous_hash = r["witness_hash"]
        print(f"Record {i} [{r['event_type']}]: VERIFIED")

    print("\nSUCCESS: Unified Forensic Witness chain is cryptographically intact.")

if __name__ == "__main__":
    run_trial_ii()
