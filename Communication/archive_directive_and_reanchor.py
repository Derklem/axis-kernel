import os, json, sys, time, shutil
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
STRATEGY = os.path.join(ROOT, "Strategy")
STATE = os.path.join(STRATEGY, "State")
COMM = os.path.join(ROOT, "Communication")

STATE_FILE = os.path.join(STATE, "strategy_state.json")
ANCHOR_FILE = os.path.join(STATE, "calibration_continuity_anchor.json")
CAND_FILE = os.path.join(STATE, "claim_candidates.json")
ARCHIVE_DIR = os.path.join(COMM, "ARCHIVE", "quarantine_purges")

os.makedirs(ARCHIVE_DIR, exist_ok=True)

stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

# 1. Archive the candidate
with open(CAND_FILE, "r", encoding="utf-8-sig") as f:
    cand_data = json.load(f)

archived_cands = {}
cands = cand_data.get("candidates", {})
to_remove = []

for k, v in cands.items():
    blob = json.dumps(v, ensure_ascii=False)
    if "USER_DIRECTIVE" in blob or "sovereign_intent" in blob:
        archived_cands[k] = v
        to_remove.append(k)

for k in to_remove:
    cands.pop(k)

with open(CAND_FILE, "w", encoding="utf-8") as f:
    json.dump(cand_data, f, indent=4, ensure_ascii=False)

if archived_cands:
    with open(os.path.join(ARCHIVE_DIR, f"purged_directive_{stamp}.json"), "w", encoding="utf-8") as f:
        json.dump(archived_cands, f, indent=4)

# 2. Re-anchor State
sys.path.append(STRATEGY)
from strategy_engine import StrategyEngine

with open(STATE_FILE, "r", encoding="utf-8-sig") as f:
    state = json.load(f)

ledger = state["mission_shadow_v2"]

ledger.setdefault("recovery_history", []).append({
    "ts_utc": datetime.now(timezone.utc).isoformat(),
    "reason": "directive_archived_and_forensic_reanchor",
    "purged_candidates": to_remove
})

engine = StrategyEngine()
new_hash = engine._compute_calibration_hash(
    ledger,
    override_witness_head=ledger.get("witness_chain_head")
)

ledger["calibration_ledger_integrity"]["hash"] = new_hash
ledger["calibration_ledger_integrity"]["status"] = "valid"
ledger["calibration_ledger_integrity"]["continuity_status"] = "intact"
ledger.get("calibration_ledger_integrity", {}).pop("break_reason", None)

state["mission_shadow_v2"] = ledger
with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=4, ensure_ascii=False)

with open(ANCHOR_FILE, "r", encoding="utf-8-sig") as f:
    anchor = json.load(f)

anchor["last_hash"] = new_hash
anchor["last_cycle"] = ledger.get("cycle_count")
anchor["witness_chain_head"] = ledger.get("witness_chain_head")
anchor["status"] = "valid"
anchor["continuity_status"] = "intact"
anchor["ts"] = time.time()

with open(ANCHOR_FILE, "w", encoding="utf-8") as f:
    json.dump(anchor, f, indent=4, ensure_ascii=False)

print("SUCCESS: Directive archived. System re-anchored to valid state.")
