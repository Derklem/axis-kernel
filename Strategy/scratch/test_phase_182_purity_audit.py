import os, sys, json, time, shutil, glob
from datetime import datetime, timezone

# Add Strategy to path
STRATEGY_DIR = os.path.abspath(r'd:\Infinite\Infinity\Strategy')
sys.path.append(STRATEGY_DIR)

from strategy_engine import StrategyEngine, CORE_SOURCE_REGISTRY
from axis_crypto_helpers import _hash_file_stream

def super_clean():
    print(f"Cleaning up for Phase 182 Purity Audit at {STRATEGY_DIR}...")
    
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
    purge_dir(os.path.join(STRATEGY_DIR, "State", "Forensics"))
    
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

    # Models - Use fixed timestamp for deterministic baseline hashing
    empty_model = {"entities": {}, "claims": {}, "last_updated_utc": "2026-05-10T00:00:00+00:00"}
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
        reason="phase_182_audit_start",
        shadow_ledger=engine.shadow_ledger
    )
    
    # 3. Synchronize Strategy State
    ledger = engine.shadow_ledger
    ledger["witness_chain_head"] = genesis_head
    ledger["cycle_count"] = 0
    
    # Ensure baseline hash is absolutely correct
    actual_baseline_hash = _hash_file_stream(baseline_file, "ecosystem_baseline")
    ledger["baseline_model_hash"] = actual_baseline_hash
    print(f"Genesis Baseline Hash: {actual_baseline_hash[:12]}")
    
    for name, rel_path in CORE_SOURCE_REGISTRY.items():
        abs_path = os.path.abspath(os.path.join(STRATEGY_DIR, rel_path))
        if os.path.exists(abs_path):
            ledger[f"expected_{name}_hash"] = _hash_file_stream(abs_path, "ecosystem_baseline" if name == "baseline_model" else "crypto_lint_file")

    # 4. Compute Calibration Hash
    actual_hash = engine._compute_calibration_hash(ledger, override_witness_head=genesis_head)
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
    
    # 6. Candidates
    cand_file = os.path.join(STRATEGY_DIR, "State", "claim_candidates.json")
    with open(cand_file, "w") as f: json.dump({"candidates": {}}, f, indent=4)
    
    print(f"Re-anchored at {actual_hash[:12]} (Witness: {genesis_head[:12]})")

def ingest_batch(batch_name):
    batch_path = os.path.join(STRATEGY_DIR, "scratch", "batches_182", f"{batch_name}.json")
    inquiry_dir = r'd:\infinite\Infinity\Inquiry'
    if not os.path.exists(batch_path):
        print(f"WARNING: Batch file {batch_path} not found.")
        return
        
    with open(batch_path, "r") as f: observations = json.load(f)
    for i, obs in enumerate(observations):
        obs_path = os.path.join(inquiry_dir, f"obs_{batch_name}_{i}_{int(time.time()*1000)}.observation")
        with open(obs_path, "w") as f: json.dump(obs, f, indent=4)
    print(f"Ingested {len(observations)} observations from {batch_name}")

def run_phase_182():
    super_clean()
    
    # Important: Re-initialize the Strategy Engine AFTER super_clean has written the clean state files
    engine = StrategyEngine()
    
    total_cycles = 400
    print(f"\n[+] Starting Phase 182 Witness Chain Purity Audit ({total_cycles} cycles)...")
    
    # Validate cycle 0 cleanly before looping
    anchor = engine._load_continuity_anchor()
    print(f"Cycle 0 Anchor Status: {anchor.get('status')}, Hash: {anchor.get('last_hash')[:12]}")
    
    from unittest.mock import patch
    
    with patch("subprocess.run") as mock_run, \
         patch("Warehouse.stewardship_engine.generate_proposals") as mock_stewardship, \
         patch("Warehouse.semantic_ontology_engine.index_workspace") as mock_index:
        
        mock_run.return_value = None
        mock_stewardship.return_value = None
        mock_index.return_value = None
        
        for i in range(total_cycles):
            cycle = i + 1
            if cycle == 10: ingest_batch("batch_1_quantum")
            elif cycle == 150: ingest_batch("batch_2_ai_drama")
            elif cycle == 300: ingest_batch("batch_3_finance_decay")
                
            try:
                engine.run_once()
            except Exception as e:
                print(f"FAILED at cycle {cycle}: {e}")
                break
                
            # Stop early if the cycle froze (meaning derivability or witness failed)
            status = engine.shadow_ledger.get("calibration_ledger_integrity", {}).get("status")
            if status != "valid":
                print(f"CRITICAL: Integrity status is '{status}' at cycle {cycle}. Stopping.")
                break
                
            if cycle % 100 == 0 or cycle == total_cycles:
                world_model = engine.ecosystem_mapper._load_model()
                entities = world_model.get("entities", {})
                print(f"\n--- Checkpoint Cycle {cycle} ---")
                print(f"Pool Size: {len(entities)} entities, {len(world_model.get('claims', {}))} claims.")
                for e_id, e in entities.items():
                    print(f"Source '{e_id}': Reliability = {e.get('reliability_index', 'N/A')}")
                
                # Verify continuous chain integrity explicitly
                chain_status = engine.witness.verify_chain()
                if "BREAK" in chain_status or "TAMPER" in chain_status:
                    print(f"CRITICAL: Witness chain failed at cycle {cycle}: {chain_status}")
                    sys.exit(1)
                else:
                    print("Witness Chain Integrity: INTACT")
                    
                baseline_path = os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json")
                baseline_hash = engine.shadow_ledger.get("baseline_model_hash")
                
                ok, diff = engine.ecosystem_mapper.verify_state_derivability(
                    world_model, engine.receipt_dir, baseline_path, baseline_hash, current_candidates=engine.ecosystem_mapper._load_candidates()
                )
                if not ok:
                    print(f"CRITICAL: Derivability Failure at Cycle {cycle}!")
                    print(diff)
                    sys.exit(1)
                else:
                    print("Model Derivability: VERIFIED")

    print("\n[+] Phase 182 Endurance Gauntlet Finished!")
    
if __name__ == "__main__":
    run_phase_182()
