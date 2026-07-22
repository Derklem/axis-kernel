import json
import time
import sys
import hashlib

STRATEGY_DIR = r"d:\Infinite\Infinity\Strategy"
STATE_FILE = rf"{STRATEGY_DIR}\State\strategy_state.json"
LINT_FILE = rf"{STRATEGY_DIR}\test_phase_80_ast_crypto_lint.py"

def _hash_file_stream(path, domain, chunk_size=65536):
    sha = hashlib.sha256(f"AXIS::{domain}::".encode("utf-8"))
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha.update(chunk)
    return sha.hexdigest()

def inject_reanchor():
    actual_hash = _hash_file_stream(LINT_FILE, "crypto_lint_file")
    print(f"Computed crypto_lint_file hash: {actual_hash}")
    
    with open(STATE_FILE, 'r') as f:
        state = json.load(f)
    ledger = state["mission_shadow_v2"]
    
    request = {
        "status": "pending",
        "nonce": f"reanchor_phase_82_{int(time.time())}",
        "operator": "HALCYON_ROOT",
        "reason": "Phase 82 Lint File Integrity Re-anchor",
        "scope": "temporal_continuity",
        "mode": "forensic_repair",
        "requested_cycle": ledger["cycle_count"],
        "expires_cycle": ledger["cycle_count"] + 10,
        "acknowledge_lineage_break": True,
        "new_crypto_lint_hash": actual_hash
    }
    
    ledger["continuity_reanchor_request"] = request
    
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)
    print("Injected Re-anchor Request for Phase 82.")

if __name__ == "__main__":
    inject_reanchor()
