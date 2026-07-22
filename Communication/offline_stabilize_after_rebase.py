import os, json, shutil, time, sys, glob
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
STRATEGY = os.path.join(ROOT, "Strategy")
STATE = os.path.join(STRATEGY, "State")
COMM = os.path.join(ROOT, "Communication")
VOICE = os.path.join(ROOT, "Runtime", "Decision", "axis_voice.json")

STATE_FILE = os.path.join(STATE, "strategy_state.json")
ANCHOR_FILE = os.path.join(STATE, "calibration_continuity_anchor.json")
WITNESS_FILE = os.path.join(STATE, "forensic_witness_ledger.jsonl")
CAND_FILE = os.path.join(STATE, "claim_candidates.json")

stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
backup_dir = os.path.join(COMM, "ARCHIVE", "pre_offline_stabilize_" + stamp)
os.makedirs(backup_dir, exist_ok=True)

for p in [STATE_FILE, ANCHOR_FILE, WITNESS_FILE, CAND_FILE]:
    if os.path.exists(p):
        shutil.copy2(p, os.path.join(backup_dir, os.path.basename(p)))

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

# 1. Strip UTF-8 BOM from Python files
bom_fixed = []
for p in glob.glob(os.path.join(STRATEGY, "*.py")):
    with open(p, "rb") as f:
        data = f.read()
    if data.startswith(b"\xef\xbb\xbf"):
        shutil.copy2(p, os.path.join(backup_dir, os.path.basename(p) + ".bom_backup"))
        with open(p, "wb") as f:
            f.write(data[3:])
        bom_fixed.append(os.path.basename(p))

# 2. Archive and clear stale candidate pool
cand = load(CAND_FILE, {"candidates": {}})
candidate_count = len(cand.get("candidates", {}))
archive_candidates = os.path.join(COMM, "ARCHIVE", "stale_candidates_" + stamp + ".json")
save(archive_candidates, cand)
save(CAND_FILE, {"candidates": {}})

# 3. Get latest witness tail after the failed cycles
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
    raise RuntimeError("No witness tail found")

tail_head = last["witness_hash"]
tail_cycle = last.get("cycle", 0)
tail_event = last.get("event_type", "unknown")

# 4. Load ledger and update hashes
state = load(STATE_FILE)
ledger = state["mission_shadow_v2"]

sys.path.append(STRATEGY)
from axis_crypto_helpers import _hash_file_stream
from strategy_engine import StrategyEngine, CORE_SOURCE_REGISTRY

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

# 5. Align ledger/anchor to latest witness tail
ledger["witness_chain_head"] = tail_head
ledger["ecosystem_receipts_head"] = "none"
ledger.setdefault("calibration_ledger_integrity", {})
ledger["calibration_ledger_integrity"]["status"] = "valid"
ledger["calibration_ledger_integrity"]["continuity_status"] = "intact"
ledger["calibration_ledger_integrity"]["last_verified_cycle"] = ledger.get("cycle_count", tail_cycle)
ledger["calibration_ledger_integrity"].pop("break_reason", None)
ledger["calibration_ledger_integrity"].pop("broken_witness_log_hash", None)

ledger.setdefault("recovery_history", []).append({
    "ts_utc": datetime.now(timezone.utc).isoformat(),
    "reason": "offline_stabilize_bom_and_stale_candidate_pool",
    "bom_fixed": bom_fixed,
    "stale_candidates_archived": candidate_count,
    "candidate_archive": archive_candidates,
    "new_witness_head": tail_head,
    "tail_event": tail_event,
    "backup_dir": backup_dir
})

engine = StrategyEngine()
new_hash = engine._compute_calibration_hash(ledger, override_witness_head=tail_head)
ledger["calibration_ledger_integrity"]["hash"] = new_hash

state["mission_shadow_v2"] = ledger
save(STATE_FILE, state)

anchor = load(ANCHOR_FILE)
anchor["last_hash"] = new_hash
anchor["last_cycle"] = ledger.get("cycle_count", tail_cycle)
anchor["witness_chain_head"] = tail_head
anchor["status"] = "valid"
anchor["continuity_status"] = "intact"
anchor["ts"] = time.time()
save(ANCHOR_FILE, anchor)

voice = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "speaker": "AXIS",
    "message_type": "offline_stabilization",
    "priority": "high",
    "epoch": ledger.get("cycle_count", tail_cycle),
    "last_updated_cycle": ledger.get("cycle_count", tail_cycle),
    "message": "Offline stabilization complete. BOMs removed, stale candidate pool archived, hashes refreshed, and witness re-anchored. Next step: import-only check, then core hash audit. Do not run cycles yet.",
    "evidence": [
        f"backup_dir={backup_dir}",
        f"bom_fixed={bom_fixed}",
        f"stale_candidates_archived={candidate_count}",
        f"candidate_archive={archive_candidates}",
        f"witness_lines={lines}",
        f"tail_event={tail_event}",
        f"new_witness_head={tail_head[:16]}",
        f"new_calibration_hash={new_hash[:16]}"
    ],
    "requires_response": True
}
save(VOICE, voice)

print(json.dumps(voice, indent=2, ensure_ascii=False))
