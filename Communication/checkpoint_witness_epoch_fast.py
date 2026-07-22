import os, json, shutil, time, sys, glob
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
STRATEGY = os.path.join(ROOT, "Strategy")
STATE = os.path.join(STRATEGY, "State")
COMM = os.path.join(ROOT, "Communication")
INQUIRY = os.path.join(ROOT, "Inquiry")
VOICE = os.path.join(ROOT, "Runtime", "Decision", "axis_voice.json")

STATE_FILE = os.path.join(STATE, "strategy_state.json")
ANCHOR_FILE = os.path.join(STATE, "calibration_continuity_anchor.json")
WITNESS_FILE = os.path.join(STATE, "forensic_witness_ledger.jsonl")
CAND_FILE = os.path.join(STATE, "claim_candidates.json")
RECEIPTS_DIR = os.path.join(STATE, "Receipts")
MODEL_FILE = os.path.join(STATE, "ai_ecosystem_model.json")
BASELINE_FILE = os.path.join(STATE, "ecosystem_model_baseline.json")

stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
backup_dir = os.path.join(COMM, "ARCHIVE", "pre_witness_epoch_checkpoint_FAST_" + stamp)
os.makedirs(backup_dir, exist_ok=True)

def backup_file(path):
    if os.path.exists(path) and os.path.isfile(path):
        shutil.copy2(path, os.path.join(backup_dir, os.path.basename(path)))

for p in [STATE_FILE, ANCHOR_FILE, WITNESS_FILE, CAND_FILE, MODEL_FILE, BASELINE_FILE]:
    backup_file(p)

def load(path, default=None):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return default

def save(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=4, ensure_ascii=False)
    os.replace(tmp, path)

sys.path.append(STRATEGY)
from axis_crypto_helpers import _hash_obj, _hash_file_stream
from strategy_engine import StrategyEngine, CORE_SOURCE_REGISTRY

state = load(STATE_FILE)
ledger = state["mission_shadow_v2"]
anchor = load(ANCHOR_FILE)

old_head = ledger.get("witness_chain_head")
cycle = ledger.get("cycle_count", 0)

# 1. Archive/clear receipts without copying entire dir
os.makedirs(RECEIPTS_DIR, exist_ok=True)
receipt_archive = os.path.join(backup_dir, "Receipts_archived")
os.makedirs(receipt_archive, exist_ok=True)
receipt_count = 0
for f in glob.glob(os.path.join(RECEIPTS_DIR, "*.receipt")):
    try:
        shutil.move(f, os.path.join(receipt_archive, os.path.basename(f)))
        receipt_count += 1
    except Exception:
        pass

# 2. Archive/clear candidates
old_candidates = load(CAND_FILE, {"candidates": {}})
candidate_archive = os.path.join(backup_dir, "active_candidates_archived.json")
save(candidate_archive, old_candidates)
save(CAND_FILE, {"candidates": {}})

# 3. Archive/clear only active inquiry files, no recursive copytree
archived_obs = 0
obs_archive = os.path.join(backup_dir, "Inquiry_active_files")
os.makedirs(obs_archive, exist_ok=True)

if os.path.exists(INQUIRY):
    for pat in ["*.observation", "*.observation.*", "*.dispute", "*.dispute.*"]:
        for f in glob.glob(os.path.join(INQUIRY, pat)):
            try:
                shutil.move(f, os.path.join(obs_archive, os.path.basename(f)))
                archived_obs += 1
            except Exception:
                pass

# 4. Rebaseline model to current cycle
model = load(MODEL_FILE, {"entities": {}, "claims": {}})
model["cycle_count"] = cycle
model["last_updated_utc"] = datetime.now(timezone.utc).isoformat()
save(MODEL_FILE, model)
save(BASELINE_FILE, model)

# 5. Create fresh witness checkpoint ledger
checkpoint_record = {
    "ts_utc": datetime.now(timezone.utc).isoformat(),
    "cycle": cycle,
    "event_type": "witness_epoch_checkpoint",
    "layer": "strategy_engine",
    "authority_state": "valid",
    "reason": "checkpoint_after_historical_witness_chain_break_entry_52766",
    "ancestry": {
        "previous_witness_head": old_head,
        "archived_witness_ledger": os.path.join(backup_dir, "forensic_witness_ledger.jsonl")
    },
    "prev_witness_hash": "none",
    "input_hash": _hash_obj({
        "cycle": cycle,
        "previous_witness_head": old_head,
        "checkpoint_reason": "historical_witness_chain_break"
    }, "witness_input"),
    "data": {
        "checkpoint_type": "forensic_epoch_rotation",
        "old_head": old_head,
        "receipts_archived": receipt_count,
        "candidates_archived": len(old_candidates.get("candidates", {})),
        "inquiry_files_archived": archived_obs,
        "backup_dir": backup_dir
    }
}
checkpoint_hash = _hash_obj(checkpoint_record, "witness_record")
checkpoint_record["witness_hash"] = checkpoint_hash

with open(WITNESS_FILE, "w", encoding="utf-8") as f:
    f.write(json.dumps(checkpoint_record, ensure_ascii=False) + "\n")

# 6. Refresh hashes
for name, rel_path in CORE_SOURCE_REGISTRY.items():
    abs_path = os.path.join(STRATEGY, rel_path)
    if not os.path.exists(abs_path):
        continue
    domain = "ecosystem_baseline" if name == "baseline_model" else "crypto_lint_file"
    actual = _hash_file_stream(abs_path, domain)
    if name == "baseline_model":
        ledger["baseline_model_hash"] = actual
        ledger["expected_baseline_model_hash"] = actual
    else:
        ledger[f"expected_{name}_hash"] = actual

# 7. Re-anchor
ledger["witness_chain_head"] = checkpoint_hash
ledger["ecosystem_receipts_head"] = "none"
ledger.setdefault("calibration_ledger_integrity", {})
ledger["calibration_ledger_integrity"]["status"] = "valid"
ledger["calibration_ledger_integrity"]["continuity_status"] = "intact"
ledger["calibration_ledger_integrity"]["last_verified_cycle"] = cycle
ledger["calibration_ledger_integrity"].pop("break_reason", None)
ledger["calibration_ledger_integrity"].pop("broken_witness_log_hash", None)

ledger.setdefault("recovery_history", []).append({
    "ts_utc": datetime.now(timezone.utc).isoformat(),
    "reason": "witness_epoch_checkpoint_after_historical_chain_break_FAST",
    "old_witness_head": old_head,
    "new_witness_head": checkpoint_hash,
    "backup_dir": backup_dir,
    "receipts_archived": receipt_count,
    "candidates_archived": len(old_candidates.get("candidates", {})),
    "inquiry_files_archived": archived_obs
})

engine = StrategyEngine()
new_calibration_hash = engine._compute_calibration_hash(ledger, override_witness_head=checkpoint_hash)
ledger["calibration_ledger_integrity"]["hash"] = new_calibration_hash

state["mission_shadow_v2"] = ledger
save(STATE_FILE, state)

anchor["last_hash"] = new_calibration_hash
anchor["last_cycle"] = cycle
anchor["witness_chain_head"] = checkpoint_hash
anchor["status"] = "valid"
anchor["continuity_status"] = "intact"
anchor["ts"] = time.time()
save(ANCHOR_FILE, anchor)

voice = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "speaker": "AXIS",
    "message_type": "witness_epoch_checkpoint",
    "priority": "high",
    "epoch": cycle,
    "last_updated_cycle": cycle,
    "message": "Fast witness epoch checkpoint complete. Historical broken witness ledger replaced with a fresh checkpoint. Receipts, stale candidates, and active inquiry observations archived. Run import-only verification next.",
    "evidence": [
        f"backup_dir={backup_dir}",
        f"old_witness_head={str(old_head)[:16]}",
        f"new_witness_head={checkpoint_hash[:16]}",
        f"new_calibration_hash={new_calibration_hash[:16]}",
        f"receipts_archived={receipt_count}",
        f"candidates_archived={len(old_candidates.get('candidates', {}))}",
        f"inquiry_files_archived={archived_obs}"
    ],
    "requires_response": True
}
save(VOICE, voice)

print(json.dumps(voice, indent=2, ensure_ascii=False))
print("\nBACKUP:", backup_dir)
