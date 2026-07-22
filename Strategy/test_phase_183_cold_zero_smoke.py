import os
import json
import sys
from strategy_engine import StrategyEngine

STRATEGY_DIR = r"D:\infinite\Infinity\Strategy"

def run_cold_zero_smoke():
    print("PHASE 183: COLD ZERO SMOKE TEST")
    engine = StrategyEngine()
    
    # 1. Ingest
    print("DEBUG: Ingesting harmless smoke test claim into live system.")
    engine.shadow_ledger = engine._load_shadow_ledger()
    engine.ingest_claim_candidate(
        entity="cold_zero_probe",
        claim="Cold Zero baseline accepts new ancestry",
        source_id="cold_zero_harness",
        source_type="system_probe",
        ledger=engine.shadow_ledger
    )
    engine.shadow_ledger["calibration_ledger_integrity"]["hash"] = engine._compute_calibration_hash(
        engine.shadow_ledger,
        override_witness_head=engine.shadow_ledger.get("witness_chain_head")
    )
    engine._commit_shadow_ledger(engine.shadow_ledger)
    
    # 2. Run 3 cycles
    for i in range(3):
        print(f"\n--- CYCLE {i+1} ---")
        engine.run_once()
        
    print("\nDEBUG: Smoke test cycles complete. Auditing Derivability...")
    
    # 3. Verify
    engine.shadow_ledger = engine._load_shadow_ledger()
    model = engine.ecosystem_mapper._load_model()
    candidates = engine.ecosystem_mapper._load_candidates()
    anomalies = engine.ecosystem_mapper._load_anomalies()
    
    baseline_path = os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json")
    expected_baseline_hash = engine.ecosystem_mapper._hash_file_domain(baseline_path, "ecosystem_baseline")
    
    ok, errors = engine.ecosystem_mapper.verify_state_derivability(
        model=model,
        receipt_dir=engine.receipt_dir,
        baseline_path=baseline_path,
        expected_baseline_hash=expected_baseline_hash,
        current_candidates=candidates,
        current_anomalies=anomalies,
        expected_head=engine.shadow_ledger.get("ecosystem_receipts_head"),
        expected_cycle=engine.shadow_ledger.get("cycle_count")
    )
    
    if not ok:
        print("CRITICAL: Cold Zero Smoke Test Derivability Failed!")
        for e in errors:
            print("ERROR:", e)
        sys.exit(1)
        
    print("COLD ZERO SMOKE TEST PASSED SUCCESSFULLY.")
    
if __name__ == '__main__':
    run_cold_zero_smoke()
