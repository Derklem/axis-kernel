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
    # We do NOT save this yet. We will let run_once() process it.
    # To simulate "naturally high tension", we'll set the history to 1.0
    # but we will do it through the engine's internal mechanism if possible,
    # or just accept that the first run_once will seal the 1.0 history.
    
    print("--- PHASE 1: INJECTING HIGH TENSION ---")
    ledger["horizon_tension_score"] = 1.0
    # We'll fill history with 1.0 to ensure avg_tension > 0.5 immediately
    ledger["tension_history"] = [1.0] * 10 
    ledger["avg_tension"] = 1.0
    
    # Save the injected state once to establish the "High Entropy" starting point
    with open(ledger_path, "w") as f:
        json.dump(full_state, f, indent=4)
    
    # Sync anchor so we don't get a continuity break
    anchor_path = os.path.join(STRATEGY_DIR, "State", "calibration_continuity_anchor.json")
    with open(anchor_path, "r") as f:
        anchor = json.load(f)
    
    # We need to compute the hash of this new state to avoid broken anchor
    from axis_crypto_helpers import _hash_obj
    # This is a bit complex since compute_calibration_hash is an engine method
    # Let's just use the engine to seal it naturally in the first cycle.
    
    print("[*] High Tension injected. Running Cycle 1 (Sealing 1.0 Tension)...")
    engine.run_once()
    
    # Verify Survival Reset
    candidates_path = os.path.join(STRATEGY_DIR, "State", "claim_candidates.json")
    with open(candidates_path, "r") as f:
        cands = json.load(f)
    
    sample_id = "b378a4961f9db5b8ecd072690121694c4cf2ce9567b04eed39520d5cd5e20af7"
    survival = cands["candidates"].get(sample_id, {}).get("cycles_survived", -1)
    print(f"[*] Cycle 1 Sample Survival: {survival} (Expected: 0 due to High Tension)")

    print("\n--- PHASE 2: NATURAL COOLING (10 CYCLES) ---")
    # Reset horizon_tension_score to 0.0 for the cooling phase
    with open(ledger_path, "r") as f:
        full_state = json.load(f)
    full_state["mission_shadow_v2"]["horizon_tension_score"] = 0.0
    with open(ledger_path, "w") as f:
        json.dump(full_state, f, indent=4)
    
    # Run 10 cycles. Tension should decay 1.0 -> 0.9 -> ... -> 0.0
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
