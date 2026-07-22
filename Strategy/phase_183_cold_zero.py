import os
import json
import shutil
from datetime import datetime, timezone

ROOT = r"D:\infinite\Infinity"
STRATEGY_DIR = os.path.join(ROOT, "Strategy")
STATE_DIR = os.path.join(STRATEGY_DIR, "State")

def run_cold_zero_supersession():
    import sys
    sys.path.append(STRATEGY_DIR)
    from strategy_engine import StrategyEngine
    from ecosystem_mapping_engine import EcosystemMappingEngine

    print("PHASE 183: COLD ZERO SUPERSESSION")
    
    # 1. Create timestamped archive
    utc_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_dir = os.path.join(STATE_DIR, "Archives", f"Fractured_Receipts_{utc_str}")
    os.makedirs(archive_dir, exist_ok=True)
    
    # Move Receipts
    live_receipts = os.path.join(STATE_DIR, "Receipts")
    if os.path.exists(live_receipts):
        shutil.move(live_receipts, os.path.join(archive_dir, "Receipts"))
        
    # Copy state files
    files_to_copy = [
        "strategy_state.json",
        "ai_ecosystem_model.json",
        "speculative_candidates.json",
        "speculative_anomalies.json"
    ]
    for fn in files_to_copy:
        src = os.path.join(STATE_DIR, fn)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(archive_dir, fn))
            
    # Copy audit report
    audit_report_src = os.path.join(STRATEGY_DIR, "Audit", "phase_182_receipt_audit.md")
    if os.path.exists(audit_report_src):
        shutil.copy2(audit_report_src, os.path.join(archive_dir, "phase_182_receipt_audit.md"))
        
    print(f"Archive created at: {archive_dir}")
    
    # 2. Write FRACTURED_LINEAGE_SUPERSEDED.md
    superseded_md = os.path.join(archive_dir, "FRACTURED_LINEAGE_SUPERSEDED.md")
    with open(superseded_md, "w") as f:
        f.write("# FRACTURED LINEAGE SUPERSEDED\n\n")
        f.write("This archive contains the fractured epistemic history of the ecosystem.\n\n")
        f.write("## Findings (Phase 182 Audit)\n")
        f.write("- **Total receipts**: 454\n")
        f.write("- **Genesis roots**: 12\n")
        f.write("- **Missing Head**: The live ledger's head was entirely missing from the receipt chain.\n")
        f.write("- **Longest Valid Chain**: 336 receipts.\n")
        f.write("- **Resolution**: Repair was explicitly rejected to avoid synthesizing history. The lineage was superseded with a new Cold Zero baseline.\n")
        
    # 3. Establish new baseline
    # Recreate empty Receipts dir
    os.makedirs(live_receipts, exist_ok=True)
    
    # Overwrite baseline model with current model
    live_model = os.path.join(STATE_DIR, "ai_ecosystem_model.json")
    live_baseline = os.path.join(STATE_DIR, "ecosystem_model_baseline.json")
    if os.path.exists(live_model):
        shutil.copy2(live_model, live_baseline)
        
    # Clear candidates and anomalies
    for fn, root_key in [("speculative_candidates.json", "candidates"), ("claim_candidates.json", "candidates"), ("speculative_anomalies.json", "anomalies")]:
        p = os.path.join(STATE_DIR, fn)
        if os.path.exists(p):
            with open(p, "w") as f:
                json.dump({root_key: {}}, f)
        
    # Load and reset strategy_state
    engine = StrategyEngine()
    ledger = engine._load_shadow_ledger()
    
    # Set ecosystem_receipts_head = "none"
    ledger["ecosystem_receipts_head"] = "none"
    
    # Recompute expected hashes for all core engines
    from strategy_engine import CORE_SOURCE_REGISTRY
    from strategy_engine import _hash_file_stream
    for name, rel_path in CORE_SOURCE_REGISTRY.items():
        abs_path = os.path.join(STRATEGY_DIR, rel_path)
        domain = "ecosystem_baseline" if name == "baseline_model" else "crypto_lint_file"
        actual = _hash_file_stream(abs_path, domain) if os.path.exists(abs_path) else "MISSING"
        if name == "baseline_model":
            ledger["baseline_model_hash"] = actual
        ledger[f"expected_{name}_hash"] = actual
        
    # Seal calibration_ledger_integrity
    ledger["calibration_ledger_integrity"]["hash"] = engine._compute_calibration_hash(
        ledger, 
        override_witness_head=ledger.get("witness_chain_head")
    )
    
    # Write updated state
    engine._commit_shadow_ledger(ledger)
    
    print("Cold Zero baseline established. Live state sealed.")

if __name__ == "__main__":
    run_cold_zero_supersession()
