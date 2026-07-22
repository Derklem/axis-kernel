import os
import json
import sys

# Add strategy engine directory to path
STRATEGY_DIR = r"d:\Infinite\Infinity\Strategy"
sys.path.append(STRATEGY_DIR)
from strategy_engine import StrategyEngine

def run_clean_natural_recovery_proof():
    """
    Phase 174 Final Verification:
    Strict Natural Recovery Proof - No manual ledger edits, no private method calls.
    1. Create pressure via structural registry.
    2. Run run_once() to establish high tension.
    3. Remove pressure.
    4. Run run_once() cycles and observe natural decay and survival increment.
    """
    engine = StrategyEngine()
    
    # Paths
    ledger_path = os.path.join(STRATEGY_DIR, "State", "strategy_state.json")
    registry_path = r"d:\infinite\Warehouse\warehouse_structural_registry.json"
    candidates_path = os.path.join(STRATEGY_DIR, "State", "claim_candidates.json")
    
    # Sample candidate to track
    sample_id = "b378a4961f9db5b8ecd072690121694c4cf2ce9567b04eed39520d5cd5e20af7"

    # --- PHASE 1: ESTABLISH NATURAL PRESSURE ---
    print("--- PHASE 1: ESTABLISHING NATURAL PRESSURE ---")
    with open(registry_path, "r") as f:
        registry = json.load(f)
    
    # Inject 10 high-pressure speciated mocks to saturate history over time
    for i in range(10):
        registry["signatures"][f"MOCK_PRESSURE_{i}"] = {
            "is_speciated": True,
            "horizon_pressure": 1.0,
            "path": f"d:\\infinite\\Warehouse\\MOCK_PRESSURE_{i}"
        }
    
    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=4)
        
    print("[*] Natural pressure injected. Running 10 cycles to saturate avg_tension...")
    for i in range(10):
        engine.run_once()
        with open(ledger_path, "r") as f:
            avg = json.load(f)["mission_shadow_v2"].get("avg_tension", 0.0)
        print(f"    Cycle {i+1} Avg Tension: {avg:.2f}")

    # Check survival (should be reset)
    with open(candidates_path, "r") as f:
        cands = json.load(f)
    survival = cands["candidates"].get(sample_id, {}).get("cycles_survived", -1)
    print(f"[*] Establishment Complete. Sample Survival: {survival} (Expected: 0 if avg_tension > 0.5)")

    # --- PHASE 2: NATURAL COOLING ---
    print("\n--- PHASE 2: NATURAL COOLING ---")
    # Remove all mock pressure sources
    with open(registry_path, "r") as f:
        registry = json.load(f)
    for i in range(10):
        registry["signatures"].pop(f"MOCK_PRESSURE_{i}", None)
    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=4)
    
    print("[*] Pressure removed. Running cycles for natural decay...")
    
    # Run 12 cycles to ensure we pass the 0.5 threshold and see increments
    for i in range(1, 13):
        engine.run_once()
        with open(ledger_path, "r") as f:
            avg = json.load(f)["mission_shadow_v2"].get("avg_tension", 0.0)
        
        with open(candidates_path, "r") as f:
            cands = json.load(f)
        survival = cands["candidates"].get(sample_id, {}).get("cycles_survived", -1)
        
        print(f"[*] Cycle {i} -> Avg Tension: {avg:.2f}, Survival: {survival}")
        
    print("\n--- PROOF COMPLETE ---")

if __name__ == "__main__":
    run_clean_natural_recovery_proof()
