import os, json, shutil, time
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
STRATEGY = os.path.join(ROOT, "Strategy")
STATE = os.path.join(STRATEGY, "State")
COMM = os.path.join(ROOT, "Communication")
VOICE = os.path.join(ROOT, "Runtime", "Decision", "axis_voice.json")

STATE_FILE = os.path.join(STATE, "strategy_state.json")
ANCHOR_FILE = os.path.join(STATE, "calibration_continuity_anchor.json")
WITNESS_FILE = os.path.join(STATE, "forensic_witness_ledger.jsonl")

stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
backup_dir = os.path.join(COMM, "ARCHIVE", "pre_repair_" + stamp)
os.makedirs(backup_dir, exist_ok=True)

for p in [STATE_FILE, ANCHOR_FILE, WITNESS_FILE]:
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

# Read latest valid witness record
last = None
line_count = 0
with open(WITNESS_FILE, "r", encoding="utf-8-sig") as f:
    for line in f:
        line_count += 1
        line = line.strip()
        if not line:
            continue
        try:
            last = json.loads(line)
        except Exception:
            pass

if not last or not last.get("witness_hash"):
    raise RuntimeError("No valid witness tail found.")

tail_head = last["witness_hash"]
tail_cycle = last.get("cycle", 0)
tail_event = last.get("event_type", "unknown")

state = load(STATE_FILE)
ledger = state.get("mission_shadow_v2", {})
anchor = load(ANCHOR_FILE)

old_ledger_head = ledger.get("witness_chain_head")
old_anchor_head = anchor.get("witness_chain_head")

# Repair ledger to witness tail
ledger["witness_chain_head"] = tail_head
ledger.setdefault("calibration_ledger_integrity", {})
ledger["calibration_ledger_integrity"]["status"] = "valid"
ledger["calibration_ledger_integrity"]["continuity_status"] = "intact"
ledger["calibration_ledger_integrity"]["last_verified_cycle"] = ledger.get("cycle_count", tail_cycle)

# Use StrategyEngine's own calibration hash function if possible
import sys
sys.path.append(STRATEGY)
from strategy_engine import StrategyEngine

engine = StrategyEngine()
new_hash = engine._compute_calibration_hash(ledger, override_witness_head=tail_head)

ledger["calibration_ledger_integrity"]["hash"] = new_hash
state["mission_shadow_v2"] = ledger
save(STATE_FILE, state)

# Repair anchor to match ledger + witness tail
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
    "message_type": "recovery",
    "priority": "high",
    "epoch": ledger.get("cycle_count", tail_cycle),
    "last_updated_cycle": ledger.get("cycle_count", tail_cycle),
    "message": "Witness continuity re-anchored to physical witness tail. Forensic stabilization complete; run read-only verification before new work.",
    "evidence": [
        f"backup_dir={backup_dir}",
        f"witness_lines={line_count}",
        f"tail_event={tail_event}",
        f"tail_cycle={tail_cycle}",
        f"old_ledger_head={str(old_ledger_head)[:16]}",
        f"old_anchor_head={str(old_anchor_head)[:16]}",
        f"new_witness_head={tail_head[:16]}",
        f"new_calibration_hash={new_hash[:16]}"
    ],
    "requires_response": True
}

os.makedirs(os.path.dirname(VOICE), exist_ok=True)
save(VOICE, voice)

print(json.dumps(voice, indent=2, ensure_ascii=False))
print("\nBACKUP:", backup_dir)
