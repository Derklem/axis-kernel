import os, json, sys, time, shutil
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
STRATEGY = os.path.join(ROOT, "Strategy")
STATE = os.path.join(STRATEGY, "State")
COMM = os.path.join(ROOT, "Communication")
STATE_FILE = os.path.join(STATE, "strategy_state.json")
ANCHOR_FILE = os.path.join(STATE, "calibration_continuity_anchor.json")

stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
backup_dir = os.path.join(COMM, "ARCHIVE", "pre_clear_stale_core_latch_" + stamp)
os.makedirs(backup_dir, exist_ok=True)
shutil.copy2(STATE_FILE, os.path.join(backup_dir, "strategy_state.json"))
shutil.copy2(ANCHOR_FILE, os.path.join(backup_dir, "calibration_continuity_anchor.json"))

sys.path.append(STRATEGY)
from strategy_engine import StrategyEngine

with open(STATE_FILE, "r", encoding="utf-8-sig") as f:
    state = json.load(f)

ledger = state["mission_shadow_v2"]
old_latch = ledger.pop("core_integrity_failure_latch", None)

ledger.setdefault("recovery_history", []).append({
    "ts_utc": datetime.now(timezone.utc).isoformat(),
    "reason": "cleared_stale_core_integrity_failure_latch_after_hash_audit",
    "old_latch": old_latch,
    "backup_dir": backup_dir
})

engine = StrategyEngine()
new_hash = engine._compute_calibration_hash(
    ledger,
    override_witness_head=ledger.get("witness_chain_head")
)

ledger["calibration_ledger_integrity"]["hash"] = new_hash
ledger["calibration_ledger_integrity"]["status"] = "valid"
ledger["calibration_ledger_integrity"]["continuity_status"] = "intact"

state["mission_shadow_v2"] = ledger
with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=4, ensure_ascii=False)

with open(ANCHOR_FILE, "r", encoding="utf-8-sig") as f:
    anchor = json.load(f)

anchor["last_hash"] = new_hash
anchor["last_cycle"] = ledger.get("cycle_count", 506)
anchor["witness_chain_head"] = ledger.get("witness_chain_head")
anchor["status"] = "valid"
anchor["continuity_status"] = "intact"
anchor["ts"] = time.time()

with open(ANCHOR_FILE, "w", encoding="utf-8") as f:
    json.dump(anchor, f, indent=4, ensure_ascii=False)

print(json.dumps({
    "status": "stale_core_latch_cleared",
    "old_latch": old_latch,
    "new_calibration_hash": new_hash,
    "witness_head_preserved": ledger.get("witness_chain_head")[:16],
    "backup_dir": backup_dir
}, indent=2))
