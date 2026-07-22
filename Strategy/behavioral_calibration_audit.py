import sys
import os
import json
import time

# Environmental Pathing
STRATEGY_DIR = r"d:\infinite\Infinity\Strategy"
WAREHOUSE_DIR = r"d:\infinite\Warehouse"
sys.path.append(STRATEGY_DIR)

from strategy_engine import StrategyEngine

def run_calibration_audit(cycles=50):
    print(f"COMMENCING DEEP OBSERVATION WINDOW: {cycles} cycles...")
    se = StrategyEngine()
    
    # Track metrics
    purge_proposals = []
    total_stewardship_attempts = 0
    frozen_journal_contact = 0
    nmv_values = []
    
    for i in range(cycles):
        if i % 10 == 0:
            print(f"Tick {i}/{cycles}...")
        
        # We run the engine. It will evaluate the current state.
        # Since we've frozen targets and added the MVA penalty, 
        # we expect zero or surgical actions only.
        se.run_once()
        
        # Audit the result of the tick
        # We look at the last entry in the ledger
        LEDGER_PATH = os.path.join(STRATEGY_DIR, "Strategy_Ledger.jsonl")
        if os.path.exists(LEDGER_PATH):
            with open(LEDGER_PATH, "rb") as f:
                # Seek to end and find last line
                f.seek(-2, os.SEEK_END)
                while f.read(1) != b"\n":
                    f.seek(-2, os.SEEK_CUR)
                last_line = f.readline().decode("utf-8")
                
                try:
                    proposal = json.loads(last_line)
                    if proposal.get("origin_layer") == "warehouse":
                        total_stewardship_attempts += 1
                        change = proposal.get("proposed_change", {})
                        if change.get("artifact_type") == "legacy_cleanup":
                            purge_proposals.append(proposal)
                            nmv_values.append(proposal.get("arbitration", {}).get("net_mission_value", 0))
                            
                            target = change.get("delta", {}).get("target", "")
                            if "reconciliation" in target or "trust" in target:
                                frozen_journal_contact += 1
                except:
                    pass
        
    # Analysis Report
    print("\n" + "="*40)
    print("PHASE 8 BEHAVIORAL AUDIT RESULTS")
    print("="*40)
    print(f"Cycles Observed:         {cycles}")
    print(f"Total Purge Proposals:   {len(purge_proposals)}")
    print(f"Frozen Journal Contact:  {frozen_journal_contact}")
    
    if purge_proposals:
        print("\nProposal Details:")
        for p in purge_proposals:
            p_id = p.get("proposal_id", "unknown")[:8]
            size = p.get("proposed_change", {}).get("impact_magnitude_bytes", 0)
            nmv = p.get("arbitration", {}).get("net_mission_value", 0)
            decision = p.get("oracle", {}).get("decision")
            print(f" - {p_id}: Size={size}B, NMV={nmv}, Decision={decision}")
            
        avg_nmv = sum(nmv_values) / len(nmv_values)
        print(f"\nAverage Stewardship NMV: {avg_nmv:.2f}")
    else:
        print("\nNo Stewardship Purges Proposed. 'MVA Silence' is absolute.")
    
    print("="*40)

if __name__ == "__main__":
    run_calibration_audit(50)
