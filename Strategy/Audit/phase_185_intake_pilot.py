import os
import sys
import json
import glob
from collections import defaultdict

STRATEGY_DIR = r"D:\infinite\Infinity\Strategy"
sys.path.append(STRATEGY_DIR)
from strategy_engine import StrategyEngine
from ecosystem_mapping_engine import EcosystemMappingEngine

def run_phase_185():
    print("PHASE 185: MINIMAL REAL INTAKE PILOT")
    print("====================================")
    
    engine = StrategyEngine()
    mapper = EcosystemMappingEngine(root_dir=STRATEGY_DIR)
    
    # Reload shadow ledger to ensure we start from the correct head
    engine.shadow_ledger = engine._load_shadow_ledger()
    
    # 1. Ingest 3 claims
    print("\n[1/3] Ingesting claims...")
    
    claims = [
        {
            "entity": "factual_benchmark",
            "claim": "The ecosystem receipt chain maintains exactly one genesis root after Cold Zero supersession.",
            "source_type": "system_probe"
        },
        {
            "entity": "ambiguous_probe",
            "claim": "Predictive turbulence will exceed threshold 0.8 within the next 20 cycles due to compounding observation drift.",
            "source_type": "heuristic_forecast"
        },
        {
            "entity": "circular_logic_test",
            "claim": "The system is functioning perfectly because all perfectly functioning systems report that they are functioning perfectly.",
            "source_type": "weak_inference"
        }
    ]
    
    for c in claims:
        engine.ingest_claim_candidate(
            entity=c["entity"],
            claim=c["claim"],
            source_id="pilot_harness",
            source_type=c["source_type"],
            ledger=engine.shadow_ledger
        )
        
    # Commit the ledger to record the quarantines before running cycles
    engine.shadow_ledger["calibration_ledger_integrity"]["hash"] = engine._compute_calibration_hash(
        engine.shadow_ledger,
        override_witness_head=engine.shadow_ledger.get("witness_chain_head")
    )
    engine._commit_shadow_ledger(engine.shadow_ledger)
    
    # Get IDs for tracking
    ids = {
        "benign": mapper.get_claim_id("factual_benchmark", claims[0]["claim"]),
        "ambiguous": mapper.get_claim_id("ambiguous_probe", claims[1]["claim"]),
        "weak": mapper.get_claim_id("circular_logic_test", claims[2]["claim"])
    }
    
    print("\nTracking IDs:")
    for k, v in ids.items():
        print(f" - {k.capitalize()}: {v}")
        
    # 2. Run 12 cycles
    print("\n[2/3] Running 12 metabolic cycles...")
    for i in range(12):
        print(f"--- Cycle {i+1}/12 ---")
        engine.run_once()
        
    # 3. Analyze Results
    print("\n[3/3] Analyzing Fates & System Integrity...")
    
    candidates = mapper._load_candidates().get("candidates", {})
    anomalies = mapper._load_anomalies().get("anomalies", {})
    
    def get_status(cid):
        if cid in candidates:
            return "CANDIDATE_POOL", candidates[cid]
        if cid in anomalies:
            return "ANOMALY_VAULT", anomalies[cid]
        return "FRACTURED/REJECTED", None
        
    print("\n--- Claim Fates ---")
    for k, cid in ids.items():
        loc, data = get_status(cid)
        print(f"{k.capitalize()} Claim ({cid[:8]}...):")
        print(f"  Location: {loc}")
        if data:
            if loc == "CANDIDATE_POOL":
                print(f"  Confidence: {data.get('structural_confidence', 'N/A')}")
            elif loc == "ANOMALY_VAULT":
                print(f"  Status: {data.get('status', 'N/A')}")
                print(f"  Reason: {data.get('suspension_reason', 'N/A')}")
        print()
        
    # Audit Receipts Directory
    receipts_dir = os.path.join(STRATEGY_DIR, "State", "Receipts")
    receipt_files = glob.glob(os.path.join(receipts_dir, "*.receipt"))
    
    by_hash = {}
    children_map = defaultdict(list)
    genesis_roots = []
    
    for r_path in receipt_files:
        with open(r_path, "r") as f:
            r = json.load(f)
            r_copy = dict(r)
            r_copy.pop("receipt_id", None)
            causal = r_copy.pop("causal_hash", None)
            parent = r.get("parent_receipt_head", "none")
            
            chain_hash = mapper._compute_domain_hash("ecosystem_receipt_chain", {"parent_head": parent, "causal_hash": causal})
            by_hash[chain_hash] = {"parent": parent, "path": r_path}
            children_map[parent].append(chain_hash)
            if parent == "none":
                genesis_roots.append(chain_hash)

    print("\n--- Chain Integrity ---")
    branch_points = [p for p, c in children_map.items() if len(c) > 1]
    
    roots_ok = len(genesis_roots) == 1
    linear_ok = len(branch_points) == 0
    
    print(f"Genesis roots: {len(genesis_roots)} {'(OK)' if roots_ok else '(FAIL)'}")
    print(f"Branch points: {len(branch_points)} {'(OK)' if linear_ok else '(FAIL)'}")
    
    # Derivability Audit
    print("\n--- Derivability Check ---")
    ledger = engine._load_shadow_ledger()
    model = mapper._load_model()
    candidates_full = mapper._load_candidates()
    anomalies_full = mapper._load_anomalies()
    
    baseline_path = os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json")
    expected_baseline_hash = mapper._hash_file_domain(baseline_path, "ecosystem_baseline")
    
    ok, errors = mapper.verify_state_derivability(
        model=model,
        receipt_dir=engine.receipt_dir,
        baseline_path=baseline_path,
        expected_baseline_hash=expected_baseline_hash,
        current_candidates=candidates_full,
        current_anomalies=anomalies_full,
        expected_head=ledger.get("ecosystem_receipts_head"),
        expected_cycle=ledger.get("cycle_count")
    )
    
    if ok:
        print("DERIVABILITY AUDIT: PASSED")
    else:
        print("DERIVABILITY AUDIT: FAILED")
        for e in errors:
            print("  ERROR:", e)

    if roots_ok and linear_ok and ok:
        print("\nPHASE 185: MINIMAL REAL INTAKE PILOT PASSED SUCCESSFULLY.")
    else:
        print("\nPHASE 185: FAILED SYSTEMIC CONSTRAINTS.")

if __name__ == '__main__':
    run_phase_185()
