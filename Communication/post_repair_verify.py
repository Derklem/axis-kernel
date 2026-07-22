import json, os
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
STATE = os.path.join(ROOT, "Strategy", "State")
VOICE = os.path.join(ROOT, "Runtime", "Decision", "axis_voice.json")

def load(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

state = load(os.path.join(STATE, "strategy_state.json"))
ledger = state["mission_shadow_v2"]
anchor = load(os.path.join(STATE, "calibration_continuity_anchor.json"))

last = None
with open(os.path.join(STATE, "forensic_witness_ledger.jsonl"), "r", encoding="utf-8-sig") as f:
    for line in f:
        try:
            last = json.loads(line)
        except:
            pass

ledger_head = ledger.get("witness_chain_head")
anchor_head = anchor.get("witness_chain_head")
tail_head = last.get("witness_hash") if last else None

ok = ledger_head == anchor_head == tail_head

voice = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "speaker": "AXIS",
    "message_type": "post_repair_verification",
    "priority": "normal" if ok else "high",
    "epoch": ledger.get("cycle_count"),
    "last_updated_cycle": ledger.get("cycle_count"),
    "message": "Post-repair verification passed. Ledger, anchor, and witness tail are synchronized. Recommended next step: one cautious non-mutating boot/preflight check." if ok else "Post-repair verification failed. Do not run cycles.",
    "evidence": [
        f"ledger_head={str(ledger_head)[:16]}",
        f"anchor_head={str(anchor_head)[:16]}",
        f"tail_head={str(tail_head)[:16]}",
        f"heads_match={ok}",
        f"integrity={ledger.get('calibration_ledger_integrity', {}).get('status')}",
        f"continuity={ledger.get('calibration_ledger_integrity', {}).get('continuity_status')}"
    ],
    "requires_response": True
}

tmp = VOICE + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(voice, f, indent=2, ensure_ascii=False)
os.replace(tmp, VOICE)

print(json.dumps(voice, indent=2, ensure_ascii=False))
