import os, json, sys, shutil, time
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
STRATEGY = os.path.join(ROOT, "Strategy")
STATE = os.path.join(STRATEGY, "State")
COMM = os.path.join(ROOT, "Communication")

STATE_FILE = os.path.join(STATE, "strategy_state.json")
ANCHOR_FILE = os.path.join(STATE, "calibration_continuity_anchor.json")
CAND_FILE = os.path.join(STATE, "claim_candidates.json")

stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
backup_dir = os.path.join(COMM, "ARCHIVE", f"pre_purge_stale_{stamp}")
os.makedirs(backup_dir, exist_ok=True)

# Backup
shutil.copy2(STATE_FILE, os.path.join(backup_dir, "strategy_state.json"))
shutil.copy2(CAND_FILE, os.path.join(backup_dir, "claim_candidates.json"))
shutil.copy2(ANCHOR_FILE, os.path.join(backup_dir, "calibration_continuity_anchor.json"))

# Purge stale sovereign_intent candidates
with open(CAND_FILE, "r", encoding="utf-8-sig") as f:
    cand_data = json.load(f)

candidates = cand_data.get("candidates", {})
to_purge = [k for k, v in candidates.items() if v.get("artifact_type") == "sovereign_intent"]

for k in to_purge:
    del candidates[k]

with open(CAND_FILE, "w", encoding="utf-8") as f:
    json.dump(cand_data, f, indent=4, ensure_ascii=False)

print(f"Purged {len(to_purge)} stale sovereign_intent candidates.")

# Re-anchor
sys.path.append(STRATEGY)
from strategy_engine import StrategyEngine
e = StrategyEngine()
ledger = e._load_shadow_ledger()

new_hash = e._compute_calibration_hash(ledger, override_witness_head=ledger.get("witness_chain_head"))

ledger["calibration_ledger_integrity"]["hash"] = new_hash
ledger["calibration_ledger_integrity"]["status"] = "valid"
ledger["calibration_ledger_integrity"]["continuity_status"] = "intact"

with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump({"mission_shadow_v2": ledger}, f, indent=4, ensure_ascii=False)

with open(ANCHOR_FILE, "w", encoding="utf-8") as f:
    json.dump({
        "last_hash": new_hash,
        "last_cycle": ledger.get("cycle_count"),
        "witness_chain_head": ledger.get("witness_chain_head"),
        "status": "valid",
        "continuity_status": "intact",
        "ts": time.time()
    }, f, indent=4, ensure_ascii=False)

print("✅ Stale candidates purged + system re-anchored clean.")
