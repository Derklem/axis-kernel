import os
import sys
sys.path.append(r"D:\infinite\Infinity")
from Strategy.strategy_engine import StrategyEngine

engine = StrategyEngine()
for i in range(25):
    try:
        engine.run_once()
        print(f"Cycle {i+1}/25 completed")
    except Exception as e:
        print(f"Cycle {i+1} failed: {e}")
        break
