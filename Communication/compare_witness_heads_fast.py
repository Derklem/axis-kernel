import json, os
from datetime import datetime

ROOT = r"D:\Infinite\Infinity"
STATE = os.path.join(ROOT, "Strategy", "State")
OUT_DIR = os.path.join(ROOT, "Communication", "FROM_AXS")

state_path = os.path.join(STATE, "strategy_state.json")
anchor_path = os.path.join(STATE, "calibration_continuity_anchor.json")
witness_path = os.path.join(STATE, "forensic_witness_ledger.jsonl")

os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, "witness_head_compare_fast_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt")

def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

state = load_json(state_path)
ledger = state.get("mission_shadow_v2", {})
anchor = load_json(anchor_path)

ledger_head = ledger.get("witness_chain_head")
anchor_head = anchor.get("witness_chain_head")

line_count = 0
last_records = []
ledger_found = 0
anchor_found = 0

if os.path.exists(witness_path):
    with open(witness_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line_count += 1
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue

            wh = rec.get("witness_hash")
            prev = rec.get("prev_witness_hash")

            if wh == ledger_head or prev == ledger_head:
                ledger_found += 1
            if wh == anchor_head or prev == anchor_head:
                anchor_found += 1

            last_records.append(rec)
            if len(last_records) > 8:
                last_records.pop(0)

last = last_records[-1] if last_records else {}

if last.get("witness_hash") == ledger_head == anchor_head:
    recommendation = "SUCCESS: Ledger, anchor, and witness tail are synchronized. No repair needed."
elif last.get("witness_hash") == ledger_head == anchor_head:
    recommendation = "SUCCESS: Ledger, anchor, and witness tail are synchronized. No repair needed."
elif ledger_found and not anchor_found:
    recommendation = "Ledger head exists in witness ledger but anchor head does not. Anchor likely stale/corrupt."
elif anchor_found and not ledger_found:
    recommendation = "Anchor head exists in witness ledger but ledger head does not. Ledger likely stale/corrupt."
else:
    recommendation = "Neither head cleanly resolves from tail. Need deeper replay before repair."

lines = []
lines.append("=== FAST WITNESS HEAD COMPARISON ===")
lines.append(f"Timestamp: {datetime.now().isoformat()}")
lines.append(f"Ledger cycle: {ledger.get('cycle_count')}")
lines.append(f"Anchor cycle: {anchor.get('last_cycle')}")
lines.append(f"Ledger head: {ledger_head}")
lines.append(f"Anchor head: {anchor_head}")
lines.append(f"Witness ledger lines: {line_count}")
lines.append("")
lines.append(f"Last witness hash: {last.get('witness_hash')}")
lines.append(f"Last event type: {last.get('event_type')}")
lines.append(f"Last cycle: {last.get('cycle')}")
lines.append("")
lines.append(f"Ledger head found count: {ledger_found}")
lines.append(f"Anchor head found count: {anchor_found}")
lines.append("")
lines.append("--- Last 8 witness records ---")
for rec in last_records:
    wh = str(rec.get("witness_hash", ""))
    prev = str(rec.get("prev_witness_hash", ""))
    lines.append(f"cycle={rec.get('cycle')} event={rec.get('event_type')} prev={prev[:16]} hash={wh[:16]}")
lines.append("")
lines.append("--- Recommendation ---")
lines.append(recommendation)

with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("\n".join(lines))
print("\nREPORT:", out)


