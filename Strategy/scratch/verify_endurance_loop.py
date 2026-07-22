import os
import sys
import time

# Add strategy dir to path
STRATEGY_DIR = r"D:\Infinite\Infinity\Strategy"
sys.path.append(STRATEGY_DIR)

from strategy_engine import StrategyEngine

def verify_endurance():
    print("[*] Verifying Endurance Loop...")
    engine = StrategyEngine()
    engine._bypass_forensic_preflight = True
    
    start_cycle = engine._load_shadow_ledger().get("cycle_count", 0)
    print(f"    - Current Cycle: {start_cycle}")
    
    target_cycles = 10
    print(f"    - Target Run: {target_cycles} cycles")
    
    for i in range(1, target_cycles + 1):
        print(f"      [Iter {i}] Running Cycle {start_cycle + i}...")
        engine.run_once()
        
    end_cycle = engine._load_shadow_ledger().get("cycle_count", 0)
    print(f"    - End Cycle: {end_cycle}")
    
    if end_cycle == start_cycle + target_cycles:
        print("[+] Endurance Loop Verified. Expected behavior confirmed.")
    else:
        print(f"[-] Endurance Loop Mismatch. Expected {start_cycle + target_cycles}, got {end_cycle}")

if __name__ == "__main__":
    verify_endurance()
