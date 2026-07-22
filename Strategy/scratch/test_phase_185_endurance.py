import os
import json
import time
import sys
from datetime import datetime, timezone

# Add strategy dir to path
STRATEGY_DIR = r"D:\Infinite\Infinity\Strategy"
sys.path.append(STRATEGY_DIR)

from strategy_engine import StrategyEngine

def run_phase_185_endurance(total_cycles=500):
    print(f"[*] Starting Phase 185: 500-Cycle Real-World Noisy Endurance...")
    engine = StrategyEngine()
    engine._bypass_forensic_preflight = True 
    
    start_time = time.time()
    
    for i in range(1, total_cycles + 1):
        try:
            print(f"DEBUG: Starting Endurance Cycle {i}...")
            engine.run_once()
            
            # Periodic Progress Report
            if i % 10 == 0:
                model = engine._load_ecosystem_model()
                candidates = engine.ecosystem_mapper._load_candidates()
                ledger = engine._load_shadow_ledger()
                
                print(f"  [Cycle {i:3}] Entities: {len(model['entities'])}, Claims: {len(model['claims'])}, Candidates: {len(candidates.get('candidates', {}))}, Tension: {ledger.get('avg_tension', 0):.3f}")
                
            # Periodic Derivability Audit
            if i % 50 == 0:
                print(f"  [Cycle {i:3}] RUNNING INDEPENDENT DERIVABILITY AUDIT...")
                ledger = engine._load_shadow_ledger()
                model = engine._load_ecosystem_model()
                candidates = engine.ecosystem_mapper._load_candidates()
                
                # Correct Signature for Phase 184/185
                ok, details = engine.ecosystem_mapper.verify_state_derivability(
                    model=model,
                    receipt_dir=engine.receipt_dir,
                    baseline_path=os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json"),
                    expected_baseline_hash=ledger.get("baseline_model_hash"),
                    current_candidates=candidates,
                    expected_head=ledger.get("ecosystem_receipts_head"),
                    expected_cycle=ledger.get("cycle_count")
                )
                
                if ok:
                    print(f"  [Cycle {i:3}] AUDIT PASSED. Forensic chain is intact.")
                else:
                    print(f"  [Cycle {i:3}] AUDIT FAILED! Forensic chain is broken.")
                    print(f"    - Details: {details}")
                    break
                    
            # Promotion Watch
            model = engine._load_ecosystem_model()
            if len(model["claims"]) > 0:
                # Track promoted claims but do NOT stop early (Phase 185 Verification Requirement)
                print(f"  [Cycle {i:3}] ALERT: Real-world promotion active!")
                for cid, cdata in model["claims"].items():
                    print(f"    - Promoted: {cdata['entity']} | {cdata.get('claim_domain', 'gen')} | Conf: {cdata['confidence']:.2f}")

        except Exception as e:
            print(f"  [Cycle {i:3}] FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            break
            
    end_time = time.time()
    duration = end_time - start_time
    print(f"\n[*] Phase 185 Endurance Run Complete.")
    
    # Final Model Snapshot
    model = engine._load_ecosystem_model()
    print(f"\n[*] Final Ecosystem Summary:")
    print(f"    - Entities: {len(model['entities'])}")
    print(f"    - Promoted Claims: {len(model['claims'])}")
    for cid, cdata in model["claims"].items():
        print(f"      [+] {cdata['entity']} ({cdata.get('claim_domain', 'unknown')}): {cdata['claim'][:60]}...")

if __name__ == "__main__":
    run_phase_185_endurance(500)
