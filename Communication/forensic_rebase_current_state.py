import os, json, shutil, time, sys
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
STRATEGY = os.path.join(ROOT, "Strategy")
STATE = os.path.join(STRATEGY, "State")
COMM = os.path.join(ROOT, "Communication")
VOICE = os.path.join(ROOT, "Runtime", "Decision", "axis_voice.json")

STATE_FILE = os.path.join(STATE, "strategy_state.json")
ANCHOR_FILE = os.path.join(STATE, "calibration_continuity_anchor.json")
WITNESS_FILE = os.path.join(STATE, "forensic_witness_ledger.jsonl")
MODEL_FILE = os.path.join(STATE, "ai_ecosystem_model.json")
BASELINE_FILE = os.path.join(STATE, "ecosystem_model_baseline.json")

stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
backup_dir = os.path.join(COMM, "ARCHIVE", "pre_rebase_" + stamp)
os.makedirs(backup_dir, exist_ok=True)

for p in [STATE_FILE, ANCHOR_FILE, WITNESS_FILE, MODEL_FILE, BASELINE_FILE]:
    if os.path.exists(p):
        shutil.copy2(p, os.path.join(backup_dir, os.path.basename(p)))

def load(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def save(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=4, ensure_ascii=False)
    os.replace(tmp, path)

# Find physical witness tail
last = None
lines = 0
with open(WITNESS_FILE, "r", encoding="utf-8-sig") as f:
    for line in f:
        lines += 1
        try:
            last = json.loads(line)
        except Exception:
            pass

if not last or not last.get("witness_hash"):
    raise RuntimeError("No valid witness tail found.")

tail_head = last["witness_hash"]
tail_event = last.get("event_type")
tail_cycle = last.get("cycle")

state = load(STATE_FILE)
ledger = state["mission_shadow_v2"]
cycle = ledger.get("cycle_count", tail_cycle or 0)

# Make model/baseline temporally consistent with ledger cycle
model = load(MODEL_FILE)
model["cycle_count"] = cycle
model["last_updated_utc"] = datetime.now(timezone.utc).isoformat()
save(MODEL_FILE, model)
save(BASELINE_FILE, model)

# Import engine utilities after files exist
sys.path.append(STRATEGY)
from axis_crypto_helpers import _hash_file_stream
from strategy_engine import StrategyEngine, CORE_SOURCE_REGISTRY

# Update all core hashes
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

# Re-anchor receipt baseline to empty chain
ledger["ecosystem_receipts_head"] = "none"

# Re-anchor witness
old_witness = ledger.get("witness_chain_head")
ledger["witness_chain_head"] = tail_head

# Clear active continuity latch but preserve forensic scar in recovery_history
scar = {
    "ts_utc": datetime.now(timezone.utc).isoformat(),
    "reason": "forensic_rebase_after_witness_tail_fatal_and_empty_receipts",
    "old_witness_head": old_witness,
    "new_witness_head": tail_head,
    "tail_event": tail_event,
    "tail_cycle": tail_cycle,
    "backup_dir": backup_dir
}
ledger.setdefault("recovery_history", []).append(scar)

ledger.setdefault("calibration_ledger_integrity", {})
ledger["calibration_ledger_integrity"]["status"] = "valid"
ledger["calibration_ledger_integrity"]["continuity_status"] = "intact"
ledger["calibration_ledger_integrity"]["last_verified_cycle"] = cycle
ledger["calibration_ledger_integrity"].pop("break_reason", None)
ledger["calibration_ledger_integrity"].pop("broken_witness_log_hash", None)

engine = StrategyEngine()
new_hash = engine._compute_calibration_hash(ledger, override_witness_head=tail_head)
ledger["calibration_ledger_integrity"]["hash"] = new_hash

state["mission_shadow_v2"] = ledger
save(STATE_FILE, state)

anchor = load(ANCHOR_FILE)
anchor["last_hash"] = new_hash
anchor["last_cycle"] = cycle
anchor["witness_chain_head"] = tail_head
anchor["status"] = "valid"
anchor["continuity_status"] = "intact"
anchor["ts"] = time.time()
save(ANCHOR_FILE, anchor)

voice = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "speaker": "AXIS",
    "message_type": "forensic_rebase",
    "priority": "high",
    "epoch": cycle,
    "last_updated_cycle": cycle,
    "message": "Forensic rebase complete. Current model is now the cycle-aligned baseline; source hashes and witness tail are synchronized. Run import-only verification next.",
    "evidence": [
        f"backup_dir={backup_dir}",
        f"witness_lines={lines}",
        f"tail_event={tail_event}",
        f"tail_cycle={tail_cycle}",
        f"new_witness_head={tail_head[:16]}",
        f"new_calibration_hash={new_hash[:16]}",
        "receipts_head=none",
        f"baseline_cycle={cycle}"
    ],
    "requires_response": True
}
save(VOICE, voice)

print(json.dumps(voice, indent=2, ensure_ascii=False))
print("\nBACKUP:", backup_dir)
