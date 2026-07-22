import os, sys, json, time, shutil, glob, hashlib
from datetime import datetime, timezone

# Add Strategy to path
STRATEGY_DIR = os.path.abspath(r'd:\Infinite\Infinity\Strategy')
sys.path.append(STRATEGY_DIR)

from strategy_engine import StrategyEngine, CORE_SOURCE_REGISTRY
from axis_crypto_helpers import _hash_file_stream

def super_clean():
    print(f"Cleaning up for Phase 181 Gauntlet at {STRATEGY_DIR}...")
    
    # Physical file removal
    def purge_dir(d, pattern="*"):
        if os.path.exists(d):
            for f in glob.glob(os.path.join(d, pattern)):
                try:
                    if os.path.isfile(f): os.remove(f)
                    elif os.path.isdir(f): shutil.rmtree(f)
                except Exception as e: print(f"Error purging {f}: {e}")

    purge_dir(os.path.join(STRATEGY_DIR, "State", "Receipts"), "*.receipt")
    purge_dir(os.path.join(STRATEGY_DIR, "State", "Archival_Exports"))
    
    for f_path in [
        os.path.join(STRATEGY_DIR, "State", "metabolic_delta_receipts.jsonl"),
        os.path.join(STRATEGY_DIR, "State", "forensic_witness_ledger.jsonl"),
        os.path.join(STRATEGY_DIR, "State", "strategy_state.json"),
        os.path.join(STRATEGY_DIR, "State", "calibration_continuity_anchor.json"),
        os.path.join(STRATEGY_DIR, "State", "ai_ecosystem_model.json"),
        os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json"),
        os.path.join(STRATEGY_DIR, "State", "claim_candidates.json"),
        r'd:\infinite\Warehouse\warehouse_structural_registry.json',
        r'd:\infinite\Warehouse\warehouse_execution_receipt.json',
        r'd:\infinite\Warehouse\warehouse_state_seq.json'
    ]:
        if os.path.exists(f_path): os.remove(f_path)
    
    inquiry_dir = r'd:\infinite\Infinity\Inquiry'
    purge_dir(inquiry_dir, "*.observation*")
    purge_dir(os.path.join(inquiry_dir, "Processed"), "*")

    # Models
    empty_model = {"entities": {}, "claims": {}, "last_updated_utc": datetime.now(timezone.utc).isoformat()}
    model_file = os.path.join(STRATEGY_DIR, "State", "ai_ecosystem_model.json")
    baseline_file = os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json")
    os.makedirs(os.path.dirname(model_file), exist_ok=True)
    with open(model_file, "w") as f: json.dump(empty_model, f, indent=4)
    with open(baseline_file, "w") as f: json.dump(empty_model, f, indent=4)
    
    # 1. Start Engine (This creates the ledger file if missing)
    engine = StrategyEngine()
    
    # 2. Force Genesis record to anchor the witness chain
    print("Emitting Genesis Witness...")
    genesis_head = engine.witness.emit(
        event_type="genesis",
        layer="strategy_engine",
        authority="axis_stewardship",
        reason="phase_181_gauntlet_start",
        shadow_ledger=engine.shadow_ledger
    )
    
    # 3. Synchronize Strategy State
    ledger = engine.shadow_ledger
    ledger["witness_chain_head"] = genesis_head
    ledger["cycle_count"] = 0
    ledger["baseline_model_hash"] = _hash_file_stream(baseline_file, "ecosystem_baseline")
    
    for name, rel_path in CORE_SOURCE_REGISTRY.items():
        abs_path = os.path.abspath(os.path.join(STRATEGY_DIR, rel_path))
        if os.path.exists(abs_path):
            ledger[f"expected_{name}_hash"] = _hash_file_stream(abs_path, "ecosystem_baseline" if name == "baseline_model" else "crypto_lint_file")

    # 4. Compute Calibration Hash
    actual_hash = engine._compute_calibration_hash(ledger)
    ledger["calibration_ledger_integrity"] = {
        "hash": actual_hash,
        "status": "valid",
        "continuity_status": "intact",
        "last_verified_cycle": 0
    }
    
    # 5. Commit State and Anchor
    with open(engine.state_file, "w") as f: json.dump({"mission_shadow_v2": ledger}, f, indent=4)
    anchor = {
        "last_hash": actual_hash,
        "last_cycle": 0,
        "witness_chain_head": genesis_head,
        "volatility_peak": 0.0,
        "volatility_caution": False,
        "status": "valid",
        "continuity_status": "intact",
        "ts": time.time()
    }
    with open(engine.anchor_file, "w") as f: json.dump(anchor, f, indent=4)
    
    # 6. Re-load engine to pick up new state
    engine = StrategyEngine()
    print(f"Re-anchored at {actual_hash[:12]} (Witness: {genesis_head[:12]})")
    
    # Candidates
    cand_file = os.path.join(STRATEGY_DIR, "State", "claim_candidates.json")
    with open(cand_file, "w") as f: json.dump({"candidates": {}}, f, indent=4)
    
    return engine

def ingest_batch(batch_name):
    batch_path = os.path.join(STRATEGY_DIR, "scratch", "batches_181", f"{batch_name}.json")
    inquiry_dir = r'd:\infinite\Infinity\Inquiry'
    with open(batch_path, "r") as f: observations = json.load(f)
    for i, obs in enumerate(observations):
        obs_path = os.path.join(inquiry_dir, f"obs_{batch_name}_{i}_{int(time.time())}.observation")
        with open(obs_path, "w") as f: json.dump(obs, f, indent=4)
    print(f"Ingested {len(observations)} observations from {batch_name}")

def run_phase_181():
    engine = super_clean()
    
    total_cycles = 260
    print(f"\n[+] Starting Phase 181 Gauntlet ({total_cycles} cycles)...")
    
    for i in range(total_cycles):
        cycle = i + 1
        if cycle == 1: ingest_batch("batch_1_apple") # Start early
        elif cycle == 50: ingest_batch("batch_2_openai")
        elif cycle == 100: ingest_batch("batch_3_contradiction")
            
        try:
            engine.run_once()
        except Exception as e:
            print(f"FAILED at cycle {cycle}: {e}")
            break
        
        if cycle % 50 == 0 or cycle == total_cycles:
            print(f"--- Cycle {cycle} complete (Model size: {len(engine.ecosystem_mapper._load_model()['entities'])}) ---")
            world_model = engine.ecosystem_mapper._load_model()
            candidates = engine.ecosystem_mapper._load_candidates()
            baseline_path = os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json")
            baseline_hash = engine.shadow_ledger.get("baseline_model_hash")
            
            ok, diff = engine.ecosystem_mapper.verify_state_derivability(
                world_model, engine.receipt_dir, baseline_path, baseline_hash, current_candidates=candidates
            )
            if not ok:
                print(f"CRITICAL: Derivability Failure at Cycle {cycle}!")
                print(diff)
                sys.exit(1)
            else:
                print(f"Derivability Verified at Cycle {cycle}.")

    print("\n[+] Gauntlet Finished Successfully!")
    model = engine.ecosystem_mapper._load_model()
    print(f"\nFinal Model Summary: {len(model['entities'])} entities, {len(model['claims'])} claims")
    for e_id, e in sorted(model['entities'].items()):
        print(f"Source '{e_id}': Reliability = {e.get('reliability_index')}")

if __name__ == "__main__":
    run_phase_181()
