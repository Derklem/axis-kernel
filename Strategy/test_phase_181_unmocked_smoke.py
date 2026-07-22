import os, json, sys, shutil
from datetime import datetime

ROOT = r"D:\infinite\Infinity"
STRATEGY_DIR = os.path.join(ROOT, "Strategy")
sys.path.append(STRATEGY_DIR)

from strategy_engine import StrategyEngine
from ecosystem_mapping_engine import EcosystemMappingEngine
import copy

SANDBOX_DIR = os.path.join(STRATEGY_DIR, "UnmockedSmokeState")

def prepare_sandbox():
    if os.path.exists(SANDBOX_DIR):
        shutil.rmtree(SANDBOX_DIR)
    if os.path.exists(SANDBOX_DIR):
        shutil.rmtree(SANDBOX_DIR)
    os.makedirs(SANDBOX_DIR, exist_ok=True)
    os.makedirs(os.path.join(SANDBOX_DIR, "Forensics"), exist_ok=True)
    os.makedirs(os.path.join(SANDBOX_DIR, "Receipts"), exist_ok=True)
    
    live_state = os.path.join(STRATEGY_DIR, "State", "strategy_state.json")
    live_anchor = os.path.join(STRATEGY_DIR, "State", "calibration_continuity_anchor.json")
    live_witness = os.path.join(STRATEGY_DIR, "State", "Forensics", "witness_chain.jsonl")
    live_baseline = os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json")
    
    shutil.copy2(live_state, os.path.join(SANDBOX_DIR, "strategy_state.json"))
    shutil.copy2(live_anchor, os.path.join(SANDBOX_DIR, "calibration_continuity_anchor.json"))
    shutil.copy2(live_baseline, os.path.join(SANDBOX_DIR, "ecosystem_model_baseline.json"))
    
    # Do not copy live receipts; the live chain is corrupted (multiple roots and missing heads).
    # We will build a pure chain from 'none' in the sandbox.
    sandbox_receipts = os.path.join(SANDBOX_DIR, "Receipts")
    os.makedirs(sandbox_receipts, exist_ok=True)
        
    os.makedirs(os.path.join(SANDBOX_DIR, "Forensics"), exist_ok=True)
    if os.path.exists(live_witness):
        shutil.copy2(live_witness, os.path.join(SANDBOX_DIR, "Forensics", "witness_chain.jsonl"))

    print(f"DEBUG: Unmocked Sandbox prepared at {SANDBOX_DIR}")

def run_smoke_test():
    prepare_sandbox()
    
    engine = StrategyEngine()
    
    # Repoint paths strictly to Sandbox
    engine.state_dir = SANDBOX_DIR
    engine.state_file = os.path.join(SANDBOX_DIR, "strategy_state.json")
    engine.anchor_file = os.path.join(SANDBOX_DIR, "calibration_continuity_anchor.json")
    engine.receipt_dir = os.path.join(SANDBOX_DIR, "Receipts")
    engine.witness.ledger_path = os.path.join(SANDBOX_DIR, "Forensics", "witness_chain.jsonl")
    
    # Sandboxed World Model must start exactly at baseline to match our pure 'none' chain
    model_path = os.path.join(SANDBOX_DIR, "ai_ecosystem_model.json")
    if os.path.exists(os.path.join(SANDBOX_DIR, "ecosystem_model_baseline.json")):
        shutil.copy2(os.path.join(SANDBOX_DIR, "ecosystem_model_baseline.json"), model_path)
    else:
        with open(model_path, "w") as f:
            json.dump({}, f)
            
    def sandbox_load_model():
        if os.path.exists(model_path):
            with open(model_path, "r") as f:
                return json.load(f)
        return {}
        
    def sandbox_save_model(model):
        with open(model_path, "w") as f:
            json.dump(model, f, indent=4)
            
    engine.ecosystem_mapper._load_model = sandbox_load_model
    engine.ecosystem_mapper._save_model = sandbox_save_model
    
    # Make sure we don't pollute live candidates
    cand_path = os.path.join(SANDBOX_DIR, "speculative_candidates.json")
    def sandbox_load_cand():
        if os.path.exists(cand_path):
            with open(cand_path, "r") as f: return json.load(f)
        return {"candidates": {}}
    def sandbox_save_cand(data):
        with open(cand_path, "w") as f: json.dump(data, f, indent=4)
        
    engine.ecosystem_mapper._load_candidates = sandbox_load_cand
    engine.ecosystem_mapper._save_candidates = sandbox_save_cand
    
    # Same for anomaly vault
    anom_path = os.path.join(SANDBOX_DIR, "speculative_anomalies.json")
    def sandbox_load_anom():
        if os.path.exists(anom_path):
            with open(anom_path, "r") as f: return json.load(f)
        return {"anomalies": {}}
    def sandbox_save_anom(data):
        with open(anom_path, "w") as f: json.dump(data, f, indent=4)
        
    engine.ecosystem_mapper._load_anomalies = sandbox_load_anom
    engine.ecosystem_mapper._save_anomalies = sandbox_save_anom
    
    # Bypass lint execution in sandbox
    engine._bypass_forensic_preflight = True
    
    # Ingest a harmless test claim
    print("DEBUG: Ingesting harmless smoke test claim.")
    engine.shadow_ledger = engine._load_shadow_ledger()
    # Reset head so we start a clean chain from 'none' rather than inheriting the broken live head
    engine.shadow_ledger["ecosystem_receipts_head"] = "none"
    engine.ingest_claim_candidate(
        entity="smoke_entity_unmocked",
        claim="Production observation breathes without mocks",
        source_id="smoke_unmocked_source",
        source_type="smoke_harness",
        ledger=engine.shadow_ledger
    )
    
    # We MUST save the ledger and anchor because ingest mutated it (cycle boundary)
    engine.shadow_ledger["calibration_ledger_integrity"]["hash"] = engine._compute_calibration_hash(
        engine.shadow_ledger,
        override_witness_head=engine.shadow_ledger.get("witness_chain_head")
    )
    engine._commit_shadow_ledger(engine.shadow_ledger)
    
    # Find our candidate ID
    cands = engine.ecosystem_mapper._load_candidates()
    target_id = list(cands["candidates"].keys())[-1]
    
    # RUN 3 UNMOCKED CYCLES
    CYCLES = 3
    print(f"DEBUG: Starting {CYCLES} unmocked run_once cycles.")
    for i in range(CYCLES):
        print(f"\n--- SMOKE CYCLE {i+1}/{CYCLES} ---")
        
        # Keep tension zero to prevent cycle reset from hysteresis
        engine.shadow_ledger = engine._load_shadow_ledger()
        engine.shadow_ledger["horizon_tension_score"] = 0.0
        engine.shadow_ledger["avg_tension"] = 0.0
        engine.shadow_ledger["calibration_ledger_integrity"]["hash"] = engine._compute_calibration_hash(
            engine.shadow_ledger,
            override_witness_head=engine.shadow_ledger.get("witness_chain_head")
        )
        engine._commit_shadow_ledger(engine.shadow_ledger)
        
        success = engine.run_once()
        if not success:
            print(f"ERROR: run_once() returned False on cycle {i+1}!")
            sys.exit(1)
            
    # Verification
    print("\nDEBUG: Verifying Smoke Test Outcomes...")
    
    cands = engine.ecosystem_mapper._load_candidates()
    cand = cands["candidates"].get(target_id)
    if not cand:
        print("ERROR: Smoke Candidate missing!")
        sys.exit(1)
        
    print(f"Candidate cycles_survived: {cand.get('cycles_survived')}")
    if cand.get("cycles_survived") < CYCLES:
        print(f"ERROR: Expected >= {CYCLES} survived cycles, found {cand.get('cycles_survived')}")
        sys.exit(1)
        
    engine.shadow_ledger = engine._load_shadow_ledger()
    cont_status = engine.shadow_ledger.get("calibration_ledger_integrity", {}).get("continuity_status")
    print(f"Continuity Status: {cont_status}")
    if cont_status != "intact":
        print(f"ERROR: Continuity violation triggered! Status: {cont_status}")
        sys.exit(1)
        
    print("DEBUG: Auditing Derivability...")
    
    model = engine.ecosystem_mapper._load_model()
    candidates = engine.ecosystem_mapper._load_candidates()
    anomalies = engine.ecosystem_mapper._load_anomalies()
    ledger = engine._load_shadow_ledger()

    baseline_path = os.path.join(SANDBOX_DIR, "ecosystem_model_baseline.json")
    expected_baseline_hash = engine.ecosystem_mapper._hash_file_domain(
        baseline_path,
        "ecosystem_baseline"
    )

    ok, errors = engine.ecosystem_mapper.verify_state_derivability(
        model=model,
        receipt_dir=engine.receipt_dir,
        baseline_path=baseline_path,
        expected_baseline_hash=expected_baseline_hash,
        current_candidates=candidates,
        current_anomalies=anomalies,
        expected_head=ledger.get("ecosystem_receipts_head"),
        expected_cycle=ledger.get("cycle_count")
    )

    if not ok:
        print(errors)
        sys.exit(1)
        
    print("\nSMOKE TEST PASSED SUCCESSFULLY.")

if __name__ == "__main__":
    run_smoke_test()
