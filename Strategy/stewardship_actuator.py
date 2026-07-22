import json
import os
import sys

# Environmental Bridging
STRATEGY_DIR = r"d:\infinite\Infinity\Strategy"
WAREHOUSE_DIR = r"d:\infinite\Warehouse"
LEDGER_PATH = os.path.join(STRATEGY_DIR, "Strategy_Ledger.jsonl")

sys.path.append(WAREHOUSE_DIR)
# Import functions directly from stewardship_engine module
import stewardship_engine

def actuate_stewardship():
    if not os.path.exists(LEDGER_PATH):
        print("ERROR: Strategy Ledger missing.")
        return

    # 1. Find the last auto_approved legacy_cleanup proposal
    last_approved = None
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                proposal = json.loads(line)
                if proposal.get("oracle", {}).get("decision") == "auto_approved" and \
                   proposal.get("proposed_change", {}).get("artifact_type") == "legacy_cleanup":
                    last_approved = proposal
            except: continue

    if not last_approved:
        print("No pending auto_approved stewardship actions found.")
        return

    change = last_approved.get("proposed_change", {})
    target = change.get("delta", {}).get("target")
    action = change.get("action")

    if not target:
        print("Malformed proposal: No target specified.")
        return

    print(f"ACTUATING: {action} on {target} (Proposal: {last_approved.get('proposal_id')})")
    
    # 2. Execute via StewardshipEngine module functions
    if action == "purge_reconciliation":
        success = stewardship_engine.execute_reconciliation_purge(target)
        if success:
            print(f"SUCCESS: {target} has been purged of legacy residue.")
        else:
            print(f"FAILED: Stewardship execution failed for {target}.")
    else:
        print(f"INFO: Action {action} not yet supported for autonomous actuation bridge.")

if __name__ == "__main__":
    actuate_stewardship()
