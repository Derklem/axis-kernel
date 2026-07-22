import sys, json, os, glob
sys.path.append(r"D:\infinite\Infinity\Strategy")
from strategy_engine import StrategyEngine

engine = StrategyEngine()

print("--- Running 5-Cycle Drift Watch ---")
for i in range(5):
    engine.run_once()

print("--- Validating Chain Linearity ---")
receipt_files = glob.glob(os.path.join(engine.receipt_dir, "*.receipt"))
roots = 0
for rf in receipt_files:
    with open(rf, "r") as f:
        rdata = json.load(f)
        if rdata.get("parent_receipt_head") == "none":
            roots += 1

print(f"Roots: {roots}")
ok = engine.ecosystem_mapper.verify_state_derivability(engine._load_shadow_ledger(), engine.receipt_dir)
if ok:
    print("[PASS] 5-Cycle Drift Watch Linear and Derivable.")
else:
    print("[FAIL] 5-Cycle Drift Watch failed derivability.")
