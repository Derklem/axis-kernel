import os, sys, json, time, shutil, glob
from datetime import datetime, timezone

# Add Strategy to path
STRATEGY_DIR = os.path.abspath(r'd:\Infinite\Infinity\Strategy')
if STRATEGY_DIR not in sys.path:
    sys.path.append(STRATEGY_DIR)

from strategy_engine import StrategyEngine, CORE_SOURCE_REGISTRY
from axis_crypto_helpers import _hash_file_stream, _hash_obj

def super_clean():
    print(f"Cleaning up for Phase 182 Endurance Gauntlet at {STRATEGY_DIR}...")
    
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
        os.path.join(STRATEGY_DIR, "State", "claim_candidates.json")
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
    
    # 1. Initialize Engine
    engine = StrategyEngine()
    
    # 2. Emit Genesis Record
    print("Emitting Genesis Witness...")
    genesis_head = engine.witness.extend(
        event_type="genesis",
        layer="strategy_engine",
        authority="axis_stewardship",
        reason="phase_182_endurance_gauntlet_start",
        shadow_ledger=engine.shadow_ledger
    )
    
    # 3. Build Initial Ledger
    ledger = engine.shadow_ledger
    ledger["witness_chain_head"] = genesis_head
    ledger["cycle_count"] = 0
    ledger["predictive_turbulence"] = {
        "score": 0.022,
        "caution_active": False,
        "last_updated_ts": 0.0,
        "threshold": 0.7,
        "drift": 0.056
    }
    
    ledger["baseline_model_hash"] = _hash_file_stream(baseline_file, "ecosystem_baseline")
    
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
        "last_verified_cycle": 0,
        "volatility_peak": 0.0,
        "volatility_caution": False
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
    
    cand_file = os.path.join(STRATEGY_DIR, "State", "claim_candidates.json")
    with open(cand_file, "w") as f: json.dump({"candidates": {}}, f, indent=4)
    
    print(f"Re-anchored at {actual_hash[:12]} (Witness: {genesis_head[:12]})")
    return engine

def ingest_random_observation(cycle):
    inquiry_dir = r'd:\infinite\Infinity\Inquiry'
    obs = {
        "entity": f"Entity_{cycle % 10}",
        "claim": f"Claim from cycle {cycle} - random data {int(time.time()) % 1000}",
        "source_id": f"Source_{cycle % 5}",
        "source_type": "endurance_gauntlet",
        "confidence": 0.5 + (0.01 * (cycle % 20)),
        "artifact_type": "ecosystem_observation",
        "ts_utc": datetime.now(timezone.utc).isoformat()
    }
    obs_path = os.path.join(inquiry_dir, f"obs_endurance_{cycle}.observation")
    with open(obs_path, "w") as f: json.dump(obs, f, indent=4)

def run_endurance_gauntlet():
    engine = super_clean()
    total_cycles = 400
    print(f"\n[+] Starting Phase 182 Endurance Gauntlet ({total_cycles} cycles)...")
    
    for i in range(total_cycles):
        cycle = i + 1
        
        # Ingest observations periodically to create mutations
        if cycle % 10 == 0:
            ingest_random_observation(cycle)
            
        try:
            engine.run_once()
        except Exception as e:
            print(f"FAILED at cycle {cycle}: {e}")
            import traceback
            traceback.print_exc()
            break
            
        # Invariant Check
        witness_head = engine.witness.last_witness_hash
        
        with open(engine.anchor_file, "r") as f:
            anchor = json.load(f)
        anchor_head = anchor.get("witness_chain_head")
        
        with open(engine.state_file, "r") as f:
            ledger = json.load(f).get("mission_shadow_v2", {})
        ledger_head = ledger.get("witness_chain_head")
        
        if not (witness_head == anchor_head == ledger_head):
            print(f"CRITICAL: Phase 182 Invariant Violation at Cycle {cycle}!")
            print(f"  Witness: {witness_head[:12]}")
            print(f"  Anchor:  {anchor_head[:12] if anchor_head else 'NONE'}")
            print(f"  Ledger:  {ledger_head[:12] if ledger_head else 'NONE'}")
            sys.exit(1)
            
        if cycle % 10 == 0:
            print(f"--- Cycle {cycle} Complete (Witness: {witness_head[:8]}) ---")
            # Verify Derivability (Diagnostic only)
            world_model = engine.ecosystem_mapper._load_model()
            candidates = engine.ecosystem_mapper._load_candidates()
            baseline_path = os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json")
            baseline_hash = engine.shadow_ledger.get("baseline_model_hash")
            
            ok, errors = engine.ecosystem_mapper.verify_state_derivability(
                world_model, engine.receipt_dir, baseline_path, baseline_hash, 
                current_candidates=candidates,
                expected_head=engine.shadow_ledger.get("ecosystem_receipts_head", "none")
            )
            if not ok:
                print(f"CRITICAL: Derivability Failure at Cycle {cycle}!")
                for err in errors: print(f"  ERROR: {err}")
                sys.exit(1)
            else:
                print(f"  Derivability Verified at Cycle {cycle}.")

    print("\n[+] Endurance Gauntlet Finished Successfully!")
    print(f"Final Cycle: {total_cycles}")
    print(f"Final Witness Head: {engine.witness.last_witness_hash}")

if __name__ == "__main__":
    run_endurance_gauntlet()
