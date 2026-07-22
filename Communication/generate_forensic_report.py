import json
import os
import hashlib
import time
from datetime import datetime

base_dir = r"D:\Infinite\Infinity\Strategy"
files_to_hash = [
    "strategy_engine.py",
    "multi_objective_solver.py",
    "axis_crypto_helpers.py",
    "ecosystem_mapping_engine.py",
    "replay_witness_chain.py"
]

def hash_file(path):
    if not os.path.exists(path): return "not_found"
    h = hashlib.sha256()
    with open(path, "rb") as f: h.update(f.read())
    return h.hexdigest()

file_hashes = {f: hash_file(os.path.join(base_dir, f)) for f in files_to_hash}

state_path = os.path.join(base_dir, "State", "strategy_state.json")
try:
    with open(state_path, "r", encoding="utf-8") as f:
        state_data = json.load(f)
except Exception as e:
    state_data = {"error": str(e)}

mission_shadow = state_data.get("mission_shadow_v2", {})
calibration_ledger_integrity = {
    "status": mission_shadow.get("status"),
    "continuity_status": mission_shadow.get("continuity_status"),
    "break_reason": mission_shadow.get("break_reason"),
    "witness_chain_head": mission_shadow.get("witness_chain_head"),
    "last_verified_cycle": mission_shadow.get("last_verified_cycle"),
    "baseline_model_hash": mission_shadow.get("baseline_model_hash")
}

core_integrity_failure_latch = mission_shadow.get("core_integrity_failure_latch", "not_present")

ledger_path = os.path.join(base_dir, "State", "forensic_witness_ledger.jsonl")
records = []
if os.path.exists(ledger_path):
    with open(ledger_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

tail_record = records[-1] if records else None

target_events = {"fatal_error", "CODE_REFACTOR_APPLIED", "CODE_REFACTOR_REJECTED", "self_improvement_applied"}
recent_filtered = [r for r in records[-50:] if r.get("event_type") in target_events]

report = {
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "file_hashes_current": file_hashes,
    "calibration_ledger_integrity": calibration_ledger_integrity,
    "core_integrity_failure_latch": core_integrity_failure_latch,
    "current_witness_tail_record": tail_record,
    "recent_target_events_last_50": recent_filtered,
    "file_changed_without_artifact_bundle": True  # True since no artifacts dir exists but files were modified
}

ts = int(time.time())
out_path = rf"D:\Infinite\Infinity\Communication\FROM_AXS\unauthorized_forensic_mutation_report_{ts}.json"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=4)

print(out_path)
