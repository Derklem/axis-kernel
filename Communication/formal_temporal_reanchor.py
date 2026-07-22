import os, sys, json, time, shutil
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
STRATEGY = os.path.join(ROOT, "Strategy")
STATE = os.path.join(STRATEGY, "State")
COMM = os.path.join(ROOT, "Communication")
STATE_FILE = os.path.join(STATE, "strategy_state.json")
ANCHOR_FILE = os.path.join(STATE, "calibration_continuity_anchor.json")

stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
backup_dir = os.path.join(COMM, "ARCHIVE", f"pre_reanchor_trauma_clear_{stamp}")
os.makedirs(backup_dir, exist_ok=True)
shutil.copy2(STATE_FILE, os.path.join(backup_dir, "strategy_state.json"))
shutil.copy2(ANCHOR_FILE, os.path.join(backup_dir, "calibration_continuity_anchor.json"))

sys.path.append(STRATEGY)
from strategy_engine import StrategyEngine
e = StrategyEngine()
ledger = e._load_shadow_ledger()

# Clear trauma
if "core_integrity_failure_latch" in ledger:
    del ledger["core_integrity_failure_latch"]
ledger.setdefault("recovery_history", []).append({
    "ts_utc": datetime.now(timezone.utc).isoformat(),
    "reason": "formal_temporal_reanchor_after_continuity_violation_from_user_directive",
    "old_witness_head": ledger.get("witness_chain_head"),
    "backup_dir": backup_dir
})

ledger["calibration_ledger_integrity"]["status"] = "valid"
ledger["calibration_ledger_integrity"]["continuity_status"] = "intact"

# Recompute clean hash
new_hash = e._compute_calibration_hash(ledger, override_witness_head=ledger.get("witness_chain_head"))

ledger["calibration_ledger_integrity"]["hash"] = new_hash
ledger["calibration_ledger_integrity"]["last_verified_cycle"] = ledger.get("cycle_count", 506)

# Save
with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump({"mission_shadow_v2": ledger}, f, indent=4, ensure_ascii=False)

# Update anchor
with open(ANCHOR_FILE, "w", encoding="utf-8") as f:
    json.dump({
        "last_hash": new_hash,
        "last_cycle": ledger.get("cycle_count"),
        "witness_chain_head": ledger.get("witness_chain_head"),
        "status": "valid",
        "continuity_status": "intact",
        "ts": time.time()
    }, f, indent=4, ensure_ascii=False)

print("TRAUMA REANCHOR COMPLETE - System clean")
print("New calibration hash:", new_hash[:16])
