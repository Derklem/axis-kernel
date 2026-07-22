import os
import json
import time
import sys

# Add strategy engine directory to path
STRATEGY_DIR = r"d:\Infinite\Infinity\Strategy"
sys.path.append(STRATEGY_DIR)
from strategy_engine import StrategyEngine

def run_cooling_test():
    engine = StrategyEngine()
    
    # 1. LOAD LEDGER
    ledger_path = os.path.join(STRATEGY_DIR, "State", "strategy_state.json")
    with open(ledger_path, "r") as f:
        full_state = json.load(f)
    ledger = full_state["mission_shadow_v2"]
    
    # 2. INJECT HIGH TENSION NATURALLY (IN MEMORY)
    print("--- PHASE 1: INJECTING HIGH TENSION ---")
    
    # To force the engine to calculate high tension NATURALLY, we mock a speciated signature
    s_path = r"d:\infinite\Warehouse\warehouse_structural_registry.json"
    with open(s_path, "r") as f:
        registry = json.load(f)
    
    # Mock a speciated file with high pressure
    registry["signatures"]["MOCK_PRESSURE_CORE"] = {
        "is_speciated": True,
        "horizon_pressure": 1.0,
        "path": "d:\\infinite\\Warehouse\\MOCK_PRESSURE_CORE"
    }
    with open(s_path, "w") as f:
        json.dump(registry, f, indent=4)
        
    # Establishment Cycle: Ledger should update horizon_tension_score to 1.0
    # and tension_history should start filling.
    # But avg_tension (sum/len) will only cross 0.5 once enough 1.0s are in.
    
    # To speed up the test, we'll preload history with 1.0s in the ledger 
    # but let run_once() do the rest.
    ledger["tension_history"] = [1.0] * 10
    ledger["avg_tension"] = 1.0
    
    with open(ledger_path, "w") as f:
        json.dump(full_state, f, indent=4)
    
    print("[*] High Tension (1.0) injected into history. Running Establishment Cycle...")
    engine.run_once()
    
    # Verify Survival Reset
    candidates_path = os.path.join(STRATEGY_DIR, "State", "claim_candidates.json")
    with open(candidates_path, "r") as f:
        cands = json.load(f)
    
    sample_id = "b378a4961f9db5b8ecd072690121694c4cf2ce9567b04eed39520d5cd5e20af7"
    survival = cands["candidates"].get(sample_id, {}).get("cycles_survived", -1)
    print(f"[*] Establishment Cycle Sample Survival: {survival} (Expected: 0 due to avg_tension=1.0)")

    print("\n--- PHASE 2: NATURAL COOLING (10 CYCLES) ---")
    # Remove the high pressure mock to allow cooling
    with open(s_path, "r") as f:
        registry = json.load(f)
    if "MOCK_PRESSURE_CORE" in registry["signatures"]:
        del registry["signatures"]["MOCK_PRESSURE_CORE"]
    with open(s_path, "w") as f:
        json.dump(registry, f, indent=4)
    
    # Run cycles. Tension history should update with 0.0s.
    # Cycle 1: history [1,1,1,1,1,1,1,1,1,0], avg = 0.9. Reset should still happen.
    # ...
    # Cycle 5: history [1,1,1,1,1,0,0,0,0,0], avg = 0.5. 
    # Cycle 6: history [1,1,1,1,0,0,0,0,0,0], avg = 0.4. Survival should advance!
    
    for i in range(1, 11):
        print(f"[*] Running Cooling Cycle {i}...")
        engine.run_once()
        with open(ledger_path, "r") as f:
            l = json.load(f)["mission_shadow_v2"]
        avg = l.get("avg_tension", 0.0)
        print(f"    Avg Tension: {avg:.2f}")
        
        with open(candidates_path, "r") as f:
            c = json.load(f)
        survival = c["candidates"].get(sample_id, {}).get("cycles_survived", -1)
        print(f"    Sample Survival: {survival}")
        
    print("\n--- TEST COMPLETE ---")

if __name__ == "__main__":
    run_cooling_test()
