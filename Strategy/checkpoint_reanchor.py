import os, json, sys, time
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
STRATEGY = os.path.join(ROOT, "Strategy")
STATE = os.path.join(STRATEGY, "State")
STATE_FILE = os.path.join(STATE, "strategy_state.json")
ANCHOR_FILE = os.path.join(STATE, "calibration_continuity_anchor.json")

sys.path.append(STRATEGY)
from strategy_engine import StrategyEngine

with open(STATE_FILE, "r", encoding="utf-8-sig") as f:
    state = json.load(f)

ledger = state["mission_shadow_v2"]

# Record formal checkpoint event
ledger.setdefault("recovery_history", []).append({
    "ts_utc": datetime.now(timezone.utc).isoformat(),
    "reason": "operator_tooling_candidate_pool_edit_without_artifact_bundle",
    "classification": "operator_tooling_candidate_pool_edit_without_artifact_bundle",
    "event_type": "formal_segment_checkpoint_reanchor"
})

engine = StrategyEngine()
new_cal_hash = engine._compute_calibration_hash(
    ledger,
    override_witness_head=ledger.get("witness_chain_head")
)

ledger["calibration_ledger_integrity"]["hash"] = new_cal_hash
ledger["calibration_ledger_integrity"]["status"] = "valid"
ledger["calibration_ledger_integrity"]["continuity_status"] = "intact"
state["mission_shadow_v2"] = ledger

with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=4, ensure_ascii=False)

with open(ANCHOR_FILE, "r", encoding="utf-8-sig") as f:
    anchor = json.load(f)
anchor["last_hash"] = new_cal_hash
anchor["status"] = "valid"
anchor["continuity_status"] = "intact"
anchor["ts"] = time.time()

with open(ANCHOR_FILE, "w", encoding="utf-8") as f:
    json.dump(anchor, f, indent=4, ensure_ascii=False)

print("Formal Segment Checkpoint Reanchor Complete.")
