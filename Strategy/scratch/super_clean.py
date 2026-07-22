import os, sys, json, glob, shutil, hashlib
from datetime import datetime, timezone

# Strategy Directory
STRATEGY_DIR = r'd:\Infinite\Infinity\Strategy'
STATE_DIR = os.path.join(STRATEGY_DIR, 'State')
INQUIRY_DIR = r'd:\Infinite\Infinity\Inquiry'

sys.path.append(STRATEGY_DIR)
from axis_crypto_helpers import _hash_file_stream

def super_clean():
    print("Performing Surgical Forensic Purge...")
    
    # 1. Clear Receipts
    receipts_dir = os.path.join(STATE_DIR, 'Receipts')
    if os.path.exists(receipts_dir):
        for f in glob.glob(os.path.join(receipts_dir, '*.receipt')):
            os.remove(f)
            
    # 2. Clear Observations & Disputes
    if os.path.exists(INQUIRY_DIR):
        for f in glob.glob(os.path.join(INQUIRY_DIR, '*.observation*')):
            os.remove(f)
        for f in glob.glob(os.path.join(INQUIRY_DIR, '*.dispute*')):
            os.remove(f)
            
    # 3. Clear Candidates
    with open(os.path.join(STATE_DIR, 'claim_candidates.json'), 'w') as f:
        json.dump({"candidates": {}}, f, indent=4)
        
    # 4. Clear Model
    # Phase 186: Use stable origin timestamp for deterministic baseline hashing
    origin_ts = "2026-05-11T00:00:00.000000+00:00"
    blank_model = {"last_updated_utc": origin_ts, "entities": {}, "claims": {}, "cycle_count": 0}
    # Use canonical serialization to ensure hash stability across different JSON implementations
    def save_canonical(data, path):
        with open(path, "w") as f:
            json.dump(data, f, indent=4, sort_keys=True)
            
    save_canonical(blank_model, os.path.join(STATE_DIR, 'ai_ecosystem_model.json'))
    save_canonical(blank_model, os.path.join(STATE_DIR, 'ecosystem_model_baseline.json'))
        
    # 4.1 Clear Structural Registry Metadata
    registry_path = r"d:\infinite\Warehouse\warehouse_structural_registry.json"
    if os.path.exists(registry_path):
        with open(registry_path, "r") as f:
            registry = json.load(f)
        
        sigs = registry.get("signatures", {})
        # Phase 187: Surgical Metadata Strip
        METABOLIC_FIELDS = ["metabolic_claims", "last_metabolic_update", "last_metabolic_cycle", "last_metabolic_receipt"]
        METABOLIC_TAGS = ["METABOLIC_VERIFIED", "METABOLIC_CONTESTED", "METABOLIC_RESTORED"]
        
        for name, sig in sigs.items():
            for field in METABOLIC_FIELDS:
                if field in sig:
                    del sig[field]
            if "tags" in sig:
                sig["tags"] = [t for t in sig["tags"] if t not in METABOLIC_TAGS]
        
        with open(registry_path, "w") as f:
            json.dump(registry, f, indent=4)
        
    # 5. Clear Witness Ledger
    witness_ledger = os.path.join(STATE_DIR, 'forensic_witness_ledger.jsonl')
    if os.path.exists(witness_ledger):
        os.remove(witness_ledger)
    with open(witness_ledger, 'w') as f:
        pass
        
    # 6. Reset Shadow Ledger
    b_hash = _hash_file_stream(os.path.join(STATE_DIR, 'ecosystem_model_baseline.json'), "ecosystem_baseline")
    
    l = {
        "mission_shadow_v2": {
            "cycle_count": 0,
            "baseline_model_hash": b_hash,
            "expected_baseline_model_hash": b_hash,
            "ecosystem_receipts_head": "none",
            "horizon_tension_score": 0.0,
            "tension_history": [],
            "avg_tension": 0.0,
            "witness_chain_head": "none",
            "calibration_ledger_integrity": {
                "status": "valid",
                "continuity_status": "intact",
                "previous_hash": "none",
                "last_verified_cycle": 0,
                "hash": "none"
            }
        }
    }
    
    # 7. Reset Anchor
    anchor_file = os.path.join(STATE_DIR, 'calibration_continuity_anchor.json')
    anchor = {
        "last_hash": "none",
        "last_cycle": 0,
        "witness_chain_head": "none",
        "status": "valid",
        "continuity_status": "intact",
        "ts": time.time()
    }
    with open(anchor_file, 'w') as f:
        json.dump(anchor, f, indent=4)
    
    # 7.1 Clear Metabolic Receipts
    receipts_dir = os.path.join(STATE_DIR, 'Receipts')
    if os.path.exists(receipts_dir):
        import shutil
        for f in os.listdir(receipts_dir):
            f_path = os.path.join(receipts_dir, f)
            try:
                if os.path.isfile(f_path): os.remove(f_path)
                elif os.path.isdir(f_path): shutil.rmtree(f_path)
            except: pass
            
    # Save ledger first so StrategyEngine can load it
    with open(os.path.join(STATE_DIR, 'strategy_state.json'), 'w') as f:
        json.dump(l, f, indent=4)
        
    # 8. Use StrategyEngine to generate a valid integrity hash
    sys.path.append(STRATEGY_DIR)
    from strategy_engine import StrategyEngine
    engine = StrategyEngine()
    
    # Re-calculate and save correctly
    ledger = engine._load_shadow_ledger()
    ledger['calibration_ledger_integrity']['hash'] = engine._compute_calibration_hash(ledger)
    engine._commit_shadow_ledger(ledger)
    
    # Update anchor with real hash
    anchor['last_hash'] = ledger['calibration_ledger_integrity']['hash']
    with open(anchor_file, 'w') as f:
        json.dump(anchor, f, indent=4)
        
    print("Purge Complete. Forensic Origin established with Valid Integrity Seal.")

if __name__ == "__main__":
    import time
    super_clean()
