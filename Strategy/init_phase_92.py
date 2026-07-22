import json
import hashlib
import os

STRATEGY_DIR = r"d:\Infinite\Infinity\Strategy"
STATE_FILE = rf"{STRATEGY_DIR}\State\strategy_state.json"

CORE_SOURCE_REGISTRY = {
    "strategy_engine": "strategy_engine.py",
    "solver_engine": "multi_objective_solver.py",
    "lint_engine": "test_phase_80_ast_crypto_lint.py",
    "trust_policy": "State/trust_lifecycle_policy.v1.json",
    "objective_policy": "State/objective_policy.json"
}

def _hash_file_stream(path, domain, chunk_size=65536):
    sha = hashlib.sha256(f"AXIS::{domain}::".encode("utf-8"))
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha.update(chunk)
    return sha.hexdigest()

def init_hashes():
    with open(STATE_FILE, 'r') as f:
        state = json.load(f)
    ledger = state["mission_shadow_v2"]
    
    for name, rel_path in CORE_SOURCE_REGISTRY.items():
        abs_path = os.path.join(STRATEGY_DIR, rel_path)
        actual = _hash_file_stream(abs_path, "crypto_lint_file")
        ledger[f"expected_{name}_hash"] = actual
        print(f"Bound {name} to {actual[:8]}")
    
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)
    print("Ledger initialized with Phase 92 core source hashes.")

if __name__ == "__main__":
    init_hashes()
