import os
import sys
import json
import time

sys.path.append(r'd:\Infinite\Infinity\Strategy')
from strategy_engine import StrategyEngine
sys.path.append(r'd:\infinite\Warehouse')
import aegis_genesis

print("=== STARTING PHASE 175 AUTONOMOUS COOLING PROOF ===")
engine = StrategyEngine()

print("\n[1] Setting AEGIS pressure to 100.0...")
aegis_genesis.set_pressure(100.0)

print("\n[2] Running run_once() 3 times under high pressure...")
for i in range(3):
    engine.run_once()
    l = engine._load_shadow_ledger()
    print(f"  Cycle: {l.get('cycle_count')} | Horizon: {l.get('horizon_tension_score')} | Avg Tension: {l.get('avg_tension')}")

l = engine._load_shadow_ledger()
if l.get("avg_tension", 0.0) > 0.0:
    print("SUCCESS: avg_tension is > 0.0")
else:
    print("FAIL: avg_tension is still 0.0")

print("\n[3] Setting AEGIS pressure to 0.0...")
aegis_genesis.set_pressure(0.0)

print("\n[4] Running run_once() until avg_tension decays...")
for i in range(15):
    engine.run_once()
    l = engine._load_shadow_ledger()
    avg_t = l.get("avg_tension", 0.0)
    print(f"  Cycle: {l.get('cycle_count')} | Horizon: {l.get('horizon_tension_score')} | Avg Tension: {avg_t}")
    if avg_t < 0.1:
        print("SUCCESS: avg_tension has decayed.")
        break

print("\n=== PROOF COMPLETE ===")
