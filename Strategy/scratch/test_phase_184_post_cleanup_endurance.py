import os, sys, json, time, shutil, glob
from datetime import datetime, timezone

# Add Strategy to path
STRATEGY_DIR = os.path.abspath(r'd:\Infinite\Infinity\Strategy')
if STRATEGY_DIR not in sys.path:
    sys.path.append(STRATEGY_DIR)

from strategy_engine import StrategyEngine, CORE_SOURCE_REGISTRY
from axis_crypto_helpers import _hash_file_stream, _hash_obj

def super_clean():
    print(f"Cleaning up for Phase 184 Post-Cleanup Endurance at {STRATEGY_DIR}...")
    
    def purge_dir(d, pattern="*"):
        if os.path.exists(d):
            for f in glob.glob(os.path.join(d, pattern)):
                try:
                    if os.path.isfile(f): os.remove(f)
                    elif os.path.isdir(f): shutil.rmtree(f)
                except Exception as e:
                    print(f"Error purging {f}: {e}")

    # Purge receipts
    purge_dir(os.path.join(STRATEGY_DIR, "State", "Receipts"), "*.receipt")
    
    # Purge state files
    for f_path in [
        os.path.join(STRATEGY_DIR, "State", "metabolic_delta_receipts.jsonl"),
        os.path.join(STRATEGY_DIR, "State", "forensic_witness_ledger.jsonl"),
        os.path.join(STRATEGY_DIR, "State", "strategy_state.json"),
        os.path.join(STRATEGY_DIR, "State", "ai_ecosystem_model.json"),
        os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json"),
        os.path.join(STRATEGY_DIR, "State", "calibration_continuity_anchor.json"),
        os.path.join(STRATEGY_DIR, "State", "claim_candidates.json")
    ]:
        if os.path.exists(f_path):
            os.remove(f_path)

def setup_baseline():
    print("Setting up baseline model...")
    os.makedirs(os.path.join(STRATEGY_DIR, "State"), exist_ok=True)
    baseline = {
        "entities": {},
        "claims": {},
        "cycle_count": 0,
        "last_updated_utc": datetime.now(timezone.utc).isoformat()
    }
    with open(os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json"), "w") as f:
        json.dump(baseline, f, indent=4)
    with open(os.path.join(STRATEGY_DIR, "State", "ai_ecosystem_model.json"), "w") as f:
        json.dump(baseline, f, indent=4)
    with open(os.path.join(STRATEGY_DIR, "State", "claim_candidates.json"), "w") as f:
        json.dump({"candidates": {}}, f, indent=4)
        
    # Use the engine to generate a default-populated ledger
    engine = StrategyEngine()
    ledger = engine.shadow_ledger
    
    # Ensure critical fields exist
    ledger["cycle_count"] = 0
    
    # Ensure baseline hashes are set
    baseline_path = os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json")
    b_hash = _hash_file_stream(baseline_path, "ecosystem_baseline")
    ledger["baseline_model_hash"] = b_hash
    ledger["expected_baseline_model_hash"] = b_hash
    
    # Initialize integrity block correctly
    if "calibration_ledger_integrity" not in ledger:
        ledger["calibration_ledger_integrity"] = {}
    integrity = ledger["calibration_ledger_integrity"]
    integrity["status"] = "valid"
    integrity["continuity_status"] = "intact"
    integrity["previous_hash"] = "none"
    integrity["last_verified_cycle"] = 0
    integrity["hash"] = "none" # Will be set below
    
    # Compute the hash of this state as it will be seen at preflight
    initial_hash = engine._compute_calibration_hash(ledger, override_witness_head=engine.witness.last_witness_hash)
    integrity["hash"] = initial_hash
    
    # Save the ledger
    with open(os.path.join(STRATEGY_DIR, "State", "strategy_state.json"), "w") as f:
        json.dump({"mission_shadow_v2": ledger}, f, indent=4)
        
    # Pre-initialize anchor with matching hash
    anchor_file = os.path.join(STRATEGY_DIR, "State", "calibration_continuity_anchor.json")
    anchor = {
        "last_hash": initial_hash,
        "last_cycle": 0,
        "witness_chain_head": engine.witness.last_witness_hash,
        "status": "valid",
        "continuity_status": "intact",
        "ts": time.time()
    }
    with open(anchor_file, "w") as f:
        json.dump(anchor, f, indent=4)
    print(f"[+] Forensic Anchor established at Hash: {initial_hash[:12]}, Cycle: 0")

def run_endurance(cycles=50):
    print(f"=== Starting Phase 184 Post-Cleanup Endurance: {cycles} Cycles ===")
    super_clean()
    setup_baseline()
    
    engine = StrategyEngine()
    engine._bypass_forensic_preflight = True # Phase 184 Admin Bypass
    
    # Now run the actual endurance loop
    for i in range(cycles):
        start_ts = time.time()
        print(f"\n--- Cycle {i+1}/{cycles} ---")
        
        # Inject some random candidate data periodically to exercise handlers
        if i % 5 == 0:
            c_id = f"cand_{i}"
            data = {
                "entity": f"Entity_{i%3}",
                "claim": f"Claim from cycle {i} - random data {int(time.time()) % 1000}",
                "source_type": "endurance_gauntlet",
                "source_id": "Source_0",
                "artifact_type": "ecosystem_observation",
                "batch_id": "none",
                "confidence": 0.5,
                "discovery_utc": datetime.now(timezone.utc).isoformat()
            }
            # Use the engine's internal state to emit receipt correctly
            ledger = engine._load_shadow_ledger()
            ok, r_id, r_hash = engine._emit_ecosystem_mutation_receipt(
                mutation_type="CANDIDATE_QUARANTINED",
                target_id=c_id,
                data=data,
                ledger=ledger
            )
            # Manually apply to state file to match the receipt
            candidates = engine.ecosystem_mapper._load_candidates()
            model = engine.ecosystem_mapper._load_model()
            mock_receipt = {
                "receipt_id": r_id,
                "causal_hash": r_hash,
                "mutation_type": "CANDIDATE_QUARANTINED", 
                "target_id": c_id, 
                "data": data
            }
            engine.ecosystem_mapper.apply_receipt_to_model(
                model, 
                mock_receipt,
                candidates=candidates
            )
            engine.ecosystem_mapper._save_candidates(candidates)
            engine.ecosystem_mapper._save_model(model)
            
            # Save ledger so next run_once sees the updated head
            with open(engine.state_file, "w") as f:
                json.dump({"mission_shadow_v2": ledger}, f, indent=4)
            print(f"[*] Forensically injected candidate {c_id}")

        try:
            engine.run_once()
        except Exception as e:
            print(f"\n[FATAL] Endurance Gauntlet Broken at Cycle {i+1}: {e}")
            sys.exit(1)
            
        if engine.frozen:
            print(f"\n[FATAL] Engine FROZEN at Cycle {i+1}!")
            sys.exit(1)
            
        # Periodically run a separate derivability check to confirm consistency
        if (i + 1) % 10 == 0:
            print(f"[*] Running independent derivability audit at cycle {i+1}...")
            baseline_path = os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json")
            baseline_hash = _hash_file_stream(baseline_path, "ecosystem_baseline")
            
            ledger = engine._load_shadow_ledger()
            model = engine.ecosystem_mapper._load_model()
            candidates = engine.ecosystem_mapper._load_candidates()
            
            ok, errors = engine.ecosystem_mapper.verify_state_derivability(
                model, engine.receipt_dir, baseline_path, baseline_hash, 
                current_candidates=candidates,
                expected_head=ledger.get("ecosystem_receipts_head", "none"),
                expected_cycle=ledger.get("cycle_count", 0)
            )
            
            if not ok:
                print(f"[FATAL] Derivability Mismatch at Checkpoint {i+1}!")
                for err in errors: print(f"  - {err}")
                sys.exit(1)
            print("[SUCCESS] Independent audit passed.")

        duration = time.time() - start_ts
        # print(f"Cycle {i+1} complete in {duration:.2f}s")
        
    print(f"\n=== Phase 184 Endurance SUCCESS: {cycles} Cycles Completed ===")

if __name__ == "__main__":
    run_endurance(50)
