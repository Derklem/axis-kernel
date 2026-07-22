import os
import sys
import json
import glob
from collections import defaultdict

STRATEGY_DIR = r"D:\infinite\Infinity\Strategy"
sys.path.append(STRATEGY_DIR)
from strategy_engine import StrategyEngine
from ecosystem_mapping_engine import EcosystemMappingEngine

def run_phase_184():
    print("PHASE 184: POST-COLD-ZERO DRIFT WATCH")
    print("======================================")

    # 7. Confirm AXIS_BYPASS_PREFLIGHT is unset/false
    bypass_env = os.environ.get("AXIS_BYPASS_PREFLIGHT", "0")
    print(f"Check: AXIS_BYPASS_PREFLIGHT = {bypass_env}")
    if bypass_env != "0":
        print("CRITICAL: AXIS_BYPASS_PREFLIGHT is active. Please disable it before drift watch.")
        sys.exit(1)

    engine = StrategyEngine()
    mapper = EcosystemMappingEngine(root_dir=STRATEGY_DIR)
    
    # Snapshot candidates/anomalies before run
    c_before = json.dumps(mapper._load_candidates(), sort_keys=True)
    a_before = json.dumps(mapper._load_anomalies(), sort_keys=True)

    # 1. Run 10 normal run_once cycles (No claims ingested)
    print("\nRunning 10 normal cycles...")
    for i in range(10):
        print(f"--- Cycle {i+1}/10 ---")
        # Run standard observation/metabolism without overrides
        engine.run_once()
        
    print("\nDrift Watch Cycles Complete. Auditing Chain Purity...")

    # Load post-run state
    ledger = engine._load_shadow_ledger()
    head = ledger.get("ecosystem_receipts_head")
    
    # Audit Receipts Directory
    receipts_dir = os.path.join(STRATEGY_DIR, "State", "Receipts")
    receipt_files = glob.glob(os.path.join(receipts_dir, "*.receipt"))
    
    print(f"\nTotal Receipts in folder: {len(receipt_files)}")
    
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

    # 4. Confirm genesis root count remains 1
    print(f"Genesis roots (parent == 'none'): {len(genesis_roots)}")
    if len(genesis_roots) != 1:
        print(f"CRITICAL: Expected exactly 1 genesis root, found {len(genesis_roots)}.")
        sys.exit(1)

    # 3. Confirm Receipts has exactly one linear chain
    branch_points = [p for p, c in children_map.items() if len(c) > 1]
    print(f"Branch points found: {len(branch_points)}")
    if len(branch_points) > 0:
        print("CRITICAL: Chain branched! Not a single linear chain.")
        sys.exit(1)

    # 5. Confirm ecosystem_receipts_head is reachable
    print(f"\nAttempting reverse walk from live head: {head}")
    curr = head
    steps = 0
    while curr and curr != "none":
        if curr not in by_hash:
            print(f"CRITICAL: Missing link in chain: {curr}")
            sys.exit(1)
        curr = by_hash[curr]["parent"]
        steps += 1
        
    print(f"Reverse walk completed back to genesis. Total chain length: {steps}")
    
    if steps != len(receipt_files):
        print(f"WARNING: Steps ({steps}) != Total Receipts ({len(receipt_files)}). There are orphaned receipts.")
    else:
        print("PERFECT MATCH: All receipts belong to the single canonical lineage.")

    # 6. Confirm candidates/anomalies remain stable
    c_after = json.dumps(mapper._load_candidates(), sort_keys=True)
    a_after = json.dumps(mapper._load_anomalies(), sort_keys=True)
    
    print("\nAuditing candidate/anomaly pools for stability...")
    c_stable = (c_before == c_after)
    a_stable = (a_before == a_after)
    
    print(f"Candidates stable: {c_stable}")
    print(f"Anomalies stable: {a_stable}")
    
    if not (c_stable and a_stable):
        print("CRITICAL: Pools drifted unexpectedly without ingested claims!")
        sys.exit(1)

    print("\nPHASE 184: POST-COLD-ZERO DRIFT WATCH PASSED SUCCESSFULLY.")

if __name__ == "__main__":
    run_phase_184()
