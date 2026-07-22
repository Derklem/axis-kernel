import os
import json
import glob
import sys
from collections import defaultdict
from ecosystem_mapping_engine import EcosystemMappingEngine

STRATEGY_DIR = r"D:\infinite\Infinity\Strategy"
LIVE_RECEIPTS_DIR = os.path.join(STRATEGY_DIR, "State", "Receipts")
LIVE_STATE_FILE = os.path.join(STRATEGY_DIR, "State", "strategy_state.json")

# Ensure python path allows importing strategy modules
sys.path.append(STRATEGY_DIR)

def run_audit():
    engine = EcosystemMappingEngine(root_dir=STRATEGY_DIR)

    print("PHASE 182: LIVE RECEIPT CHAIN PURITY AUDIT")
    print("===========================================")
    
    receipt_files = glob.glob(os.path.join(LIVE_RECEIPTS_DIR, "*.receipt"))
    print(f"1. Total receipts found: {len(receipt_files)}")
    
    receipts_list = []
    children_map = defaultdict(list)
    by_hash = {}
    genesis_roots = []
    
    for r_path in receipt_files:
        try:
            with open(r_path, "r") as f:
                r = json.load(f)
                r_copy = dict(r)
                receipt_id = r_copy.pop("receipt_id", None)
                causal = r_copy.pop("causal_hash", None)
                parent = r.get("parent_receipt_head", "none")
                
                link_data = {"parent_head": parent, "causal_hash": causal}
                chain_hash = engine._compute_domain_hash("ecosystem_receipt_chain", link_data)
                
                receipt_data = {
                    "path": r_path,
                    "id": receipt_id,
                    "parent": parent,
                    "chain_hash": chain_hash,
                    "causal_hash": causal
                }
                
                receipts_list.append(receipt_data)
                by_hash[chain_hash] = receipt_data
                children_map[parent].append(chain_hash)
                
                if parent == "none":
                    genesis_roots.append(chain_hash)
        except Exception as e:
            print(f"Warning: failed to read/parse {r_path}: {e}")
            
    print(f"2. Genesis roots (parent == 'none'): {len(genesis_roots)}")
    
    branch_points = {p: c for p, c in children_map.items() if len(c) > 1}
    print(f"3. Parent -> Children map built. Found {len(children_map)} unique parents.")
    print(f"4. Branch points (parents with >1 child): {len(branch_points)}")
    if len(branch_points) < 20:
        for p, c in branch_points.items():
            print(f"   - Parent {p[:12]}... has {len(c)} children")
    else:
        print(f"   - (Too many to list individually)")

    try:
        with open(LIVE_STATE_FILE, "r") as f:
            state_data = json.load(f)
            # Support both directly unnested ledger or nested under 'mission_shadow_v2'
            live_ledger = state_data.get("mission_shadow_v2", state_data)
        head = live_ledger.get("ecosystem_receipts_head")
    except Exception as e:
        print(f"Error loading live state: {e}")
        head = None

    print(f"\n5. Attempting reverse walk from current ecosystem_receipts_head: {head}")
    
    curr = head
    chain_length = 0
    missing_head = None
    path_taken = []
    while curr and curr != "none":
        if curr not in by_hash:
            missing_head = curr
            break
        path_taken.append(curr)
        chain_length += 1
        curr = by_hash[curr]["parent"]
        
    if missing_head:
        print(f"6. First missing head encountered: {missing_head}")
        print(f"   Reverse walk stopped after {chain_length} steps.")
    else:
        print(f"6. Reverse walk completed successfully back to genesis root.")
        print(f"   Total valid chain length from head: {chain_length}")
        
    memo = {}
    def get_max_depth(node):
        if node in memo:
            return memo[node]
        if node not in children_map or not children_map[node]:
            return 1
        max_d = 0
        for child in children_map[node]:
            if child in by_hash:
                max_d = max(max_d, get_max_depth(child))
        memo[node] = 1 + max_d
        return memo[node]
        
    longest_overall = 0
    best_root = None
    for root in genesis_roots:
        depth = get_max_depth(root)
        if depth > longest_overall:
            longest_overall = depth
            best_root = root
            
    print(f"7. Longest valid chain from any genesis root: {longest_overall} receipts.")
    if best_root:
        print(f"   (Starts at genesis root {best_root[:12]}...)")
        
    can_reconstruct = False
    if head and not missing_head:
        can_reconstruct = True
    print(f"8. Can live strategy_state be reconstructed from receipts? {'YES' if can_reconstruct else 'NO (Chain Gap)'}")

if __name__ == '__main__':
    run_audit()
