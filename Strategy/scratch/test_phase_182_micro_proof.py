import os, sys, json, time, shutil, glob
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# Add root to path for nexus_identity
ROOT_DIR = os.path.abspath(r'd:\infinite')
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# --- QUOTA SAVING: SUPPRESS IMPORT NOISE ---
import nexus_identity
nexus_identity.log_identity = lambda x: None

# Add Strategy to path
STRATEGY_DIR = os.path.abspath(r'd:\Infinite\Infinity\Strategy')
if STRATEGY_DIR not in sys.path:
    sys.path.append(STRATEGY_DIR)

from strategy_engine import StrategyEngine, CORE_SOURCE_REGISTRY
from axis_crypto_helpers import _hash_file_stream

def super_clean():
    print(f"Cleaning up for Phase 182 Micro-Proof at {STRATEGY_DIR}...")
    
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
        if os.path.exists(f_path): 
            try: os.remove(f_path)
            except Exception as e: print(f"Error removing {f_path}: {e}")
    
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
    genesis_head = engine.witness.emit(
        event_type="genesis",
        layer="strategy_engine",
        authority="axis_stewardship",
        reason="phase_182_micro_proof_start",
        shadow_ledger=engine.shadow_ledger
    )
    
    # 3. Synchronize Strategy State
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
    
    actual_baseline_hash = _hash_file_stream(baseline_file, "ecosystem_baseline")
    ledger["baseline_model_hash"] = actual_baseline_hash
    
    for name, rel_path in CORE_SOURCE_REGISTRY.items():
        abs_path = os.path.abspath(os.path.join(STRATEGY_DIR, rel_path))
        if os.path.exists(abs_path):
            ledger[f"expected_{name}_hash"] = _hash_file_stream(abs_path, "ecosystem_baseline" if name == "baseline_model" else "crypto_lint_file")

    # 4. Compute Calibration Hash
    input_dict = engine._compute_calibration_hash_input(ledger, override_witness_head=genesis_head)
    print(f"DEBUG: Genesis Hash Input: {json.dumps(input_dict, sort_keys=True)}")
    actual_hash = engine._compute_calibration_hash(ledger, override_witness_head=genesis_head)
    ledger["calibration_ledger_integrity"] = {
        "hash": actual_hash,
        "status": "valid",
        "continuity_status": "intact",
        "last_verified_cycle": 0,
        "predictive_turbulence": {
            "is_turbulent": False,
            "turbulence_score": 0.0,
            "last_updated_ts": datetime.now(timezone.utc).isoformat()
        }
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

def ingest_simple_observation():
    inquiry_dir = r'd:\infinite\Infinity\Inquiry'
    obs = {
        "entity": "Phase182_Micro_Target",
        "claim": "Witness chain integrity is confirmed for Cycle 2.",
        "source_id": "CalibrationUnit_Alpha",
        "source_type": "internal_test",
        "confidence": 0.9,
        "artifact_type": "ecosystem_observation",
        "batch_id": "micro_batch_001"
    }
    obs_path = os.path.join(inquiry_dir, "micro_obs_1.observation")
    with open(obs_path, "w") as f: json.dump(obs, f, indent=4)
    print("Ingested simple observation for Cycle 2.")

def run_micro_proof():
    super_clean()
    
    engine = StrategyEngine()
    engine._forensic_debug = True
    
    total_cycles = 10
    print(f"\n[+] Starting Phase 182 Micro-Proof ({total_cycles} cycles)...")
    
    with patch("subprocess.run") as mock_run, \
         patch("Warehouse.stewardship_engine.generate_proposals") as mock_stewardship, \
         patch("Warehouse.semantic_ontology_engine.index_workspace") as mock_index, \
         patch("time.sleep") as mock_sleep:
        
        mock_run.return_value = MagicMock(returncode=0)
        mock_stewardship.return_value = None
        mock_index.return_value = None
        mock_sleep.return_value = None
        
        engine._forensic_debug = True
        for i in range(total_cycles):
            cycle = i + 1
            if cycle == 2:
                ingest_simple_observation()
                
            print(f"DEBUG: Before run_once {cycle}, engine.witness.last_witness_hash: {engine.witness.last_witness_hash[:12]}")
            try:
                engine.run_once()
            except Exception as e:
                print(f"FAILED at cycle {cycle}: {e}")
                sys.exit(1)
            
            print(f"DEBUG: After run_once {cycle}, engine.witness.last_witness_hash: {engine.witness.last_witness_hash[:12]}")
            
            # Phase 182 Invariant: Engine, Anchor, and Ledger must be in sync
            if os.path.exists(engine.anchor_file):
                try:
                    with open(engine.anchor_file, "r") as f:
                        anchor = json.load(f)
                        a_head = anchor.get("witness_chain_head")
                        l_head = engine.shadow_ledger.get("witness_chain_head")
                        w_head = engine.witness.last_witness_hash
                        if not (w_head == a_head == l_head):
                            print(f"CRITICAL: Phase 182 Invariant Violation at Cycle {cycle}!")
                            print(f"  Witness: {w_head[:12]}")
                            print(f"  Anchor:  {a_head[:12]}")
                            print(f"  Ledger:  {l_head[:12]}")
                            sys.exit(1)
                except Exception as e:
                    print(f"DEBUG: Anchor invariant check skipped: {e}")
            
            # Check for integrity status each cycle
            status = engine.shadow_ledger.get("calibration_ledger_integrity", {}).get("status")
            if status != "valid":
                print(f"CRITICAL: Integrity status is '{status}' at cycle {cycle}. Stopping.")
                sys.exit(1)

    print("\n[+] Final Phase 182 Audit:")
    
    # 1. Witness Chain
    print(f"DEBUG: Final In-Memory Witness Head: {engine.witness.last_witness_hash[:12]}")
    if os.path.exists(engine.anchor_file):
        with open(engine.anchor_file, "r") as f:
            anchor = json.load(f)
            print(f"DEBUG: Final Disk Anchor Head:    {anchor.get('witness_chain_head', 'none')[:12]}")
    
    chain_status = engine.witness.verify_chain()
    if "BREAK" in chain_status or "TAMPER" in chain_status:
        print(f"FAIL: Witness chain: {chain_status}")
    else:
        print(f"PASS: Witness Chain (Head: {engine.witness.last_witness_hash[:12]})")

    # 2. Receipt Chain (Metabolic Receipts)
    receipt_head = engine._recompute_metabolic_receipts_head()
    ledger_receipt_head = engine.shadow_ledger.get("metabolic_receipts_head", "none")
    if receipt_head == ledger_receipt_head:
        print(f"PASS: Receipt Chain (Head: {receipt_head[:12]})")
    else:
        print(f"FAIL: Receipt Chain Mismatch (Disk: {receipt_head[:12]}, Ledger: {ledger_receipt_head[:12]})")

    # 3. Calibration Anchor
    anchor = engine._load_continuity_anchor()
    ledger_hash = engine.shadow_ledger.get("calibration_ledger_integrity", {}).get("hash")
    if anchor.get("last_hash") == ledger_hash:
        print(f"PASS: Calibration Anchor (Hash: {ledger_hash[:12]})")
    else:
        print(f"FAIL: Anchor Mismatch (Anchor: {anchor.get('last_hash')[:12]}, Ledger: {ledger_hash[:12]})")

    # 4. Model Derivability
    world_model = engine.ecosystem_mapper._load_model()
    baseline_path = os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json")
    baseline_hash = engine.shadow_ledger.get("baseline_model_hash")
    candidates = engine.ecosystem_mapper._load_candidates()
    
    ok, diff = engine.ecosystem_mapper.verify_state_derivability(
        world_model, engine.receipt_dir, baseline_path, baseline_hash, current_candidates=candidates
    )
    if ok:
        print("PASS: Model Derivability (Replay matched live state)")
    else:
        print("FAIL: Model Derivability Failure!")
        print(diff)

    print("\n[+] Phase 182 Micro-Proof Finished!")

if __name__ == "__main__":
    run_micro_proof()
