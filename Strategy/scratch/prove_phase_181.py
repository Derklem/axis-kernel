import os, sys, json
from datetime import datetime, timezone

# Add Strategy to path
STRATEGY_DIR = os.path.abspath(r'd:\Infinite\Infinity\Strategy')
sys.path.append(STRATEGY_DIR)

from ecosystem_mapping_engine import EcosystemMappingEngine
from axis_crypto_helpers import _hash_file_stream, _hash_obj

def prove_phase_181_endurance():
    print("--- Phase 181: Epistemic Metabolism 260-Cycle Endurance Proof ---")
    
    mapper = EcosystemMappingEngine(r"d:\infinite")
    model_path = os.path.join(STRATEGY_DIR, "State", "ai_ecosystem_model.json")
    baseline_path = os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json")
    receipt_dir = os.path.join(STRATEGY_DIR, "State", "Receipts")
    
    # Cleanup
    if os.path.exists(receipt_dir):
        for f in os.listdir(receipt_dir): os.remove(os.path.join(receipt_dir, f))
    else:
        os.makedirs(receipt_dir)
    
    # 1. Setup Baseline
    baseline = {
        "entities": {
            "bloomberg_wire": {"reliability_index": 0.5},
            "leaker_pro_hype": {"reliability_index": 0.5}
        },
        "claims": {},
        "last_updated_utc": datetime.now(timezone.utc).isoformat()
    }
    with open(baseline_path, "w") as f: json.dump(baseline, f, indent=4)
    baseline_hash = _hash_file_stream(baseline_path, "ecosystem_baseline")
    
    # 2. Setup Initial Model (same as baseline)
    model = json.loads(json.dumps(baseline))
    with open(model_path, "w") as f: json.dump(model, f, indent=4)
    
    # 3. Simulate 260 Cycles of Metabolism
    current_head = "none"
    total_cycles = 260
    
    print(f"\nSimulating {total_cycles} cycles...")
    
    # Cycle 0: Initial Penalty/Reward
    initial_receipts = [
        {"mutation_type": "REPUTATION_GAIN", "target_id": "bloomberg_wire", "data": {"reward_amount": 0.3}},
        {"mutation_type": "REPUTATION_PENALTY", "target_id": "leaker_pro_hype", "data": {"penalty_amount": 0.4}}
    ]
    
    all_receipts = []
    
    for r in initial_receipts:
        r["receipt_id"] = f"init_{initial_receipts.index(r)}"
        r["parent_receipt_head"] = current_head
        r_for_h = json.loads(json.dumps(r)); r_for_h.pop("receipt_id", None)
        r["causal_hash"] = _hash_obj(r_for_h, "ecosystem_receipt")
        
        mapper.apply_receipt_to_model(model, r, candidates={"candidates": {}})
        all_receipts.append(r)
        
        link_data = {"parent_head": current_head, "causal_hash": r["causal_hash"]}
        current_head = _hash_obj(link_data, "ecosystem_receipt_chain")

    print(f"Post-Injection Reliability -> Bloomberg: {model['entities']['bloomberg_wire']['reliability_index']}, Leaker: {model['entities']['leaker_pro_hype']['reliability_index']}")

    # Cycles 1 to 260: Metabolism only
    for cycle in range(1, total_cycles + 1):
        r = {"mutation_type": "ECOSYSTEM_CYCLE_COMPLETE", "cycle": cycle, "data": {}, "parent_receipt_head": current_head}
        r["receipt_id"] = f"cycle_{cycle}"
        r_for_h = json.loads(json.dumps(r)); r_for_h.pop("receipt_id", None)
        r["causal_hash"] = _hash_obj(r_for_h, "ecosystem_receipt")
        
        mapper.apply_receipt_to_model(model, r, candidates={"candidates": {}})
        all_receipts.append(r)
        
        link_data = {"parent_head": current_head, "causal_hash": r["causal_hash"]}
        current_head = _hash_obj(link_data, "ecosystem_receipt_chain")
        
        if cycle % 50 == 0:
            print(f"Cycle {cycle} complete -> Bloomberg: {model['entities']['bloomberg_wire']['reliability_index']}, Leaker: {model['entities']['leaker_pro_hype']['reliability_index']}")

    # Save ALL receipts to disk for audit
    for i, r in enumerate(all_receipts):
        r_path = os.path.join(receipt_dir, f"{i:04}_{r['mutation_type']}_{r.get('cycle', 'init')}.receipt")
        with open(r_path, "w") as f: json.dump(r, f)

    # 4. Perform Final Derivability Audit
    print("\nExecuting Final Forensic Derivability Audit (260 Cycles)...")
    ok, diff = mapper.verify_state_derivability(
        model, receipt_dir, baseline_path, baseline_hash, current_candidates={"candidates": {}}
    )
    
    if ok:
        print("SUCCESS: Full 260-cycle gauntlet is 100% derivable!")
        print(f"Final Bloomberg: {model['entities']['bloomberg_wire']['reliability_index']} (Expected drift toward 0.5)")
        print(f"Final Leaker: {model['entities']['leaker_pro_hype']['reliability_index']} (Expected drift toward 0.5)")
    else:
        print("FAILURE: Endurance derivability check failed!")
        for line in diff: print(f"  - {line}")
        sys.exit(1)

if __name__ == "__main__":
    prove_phase_181_endurance()
