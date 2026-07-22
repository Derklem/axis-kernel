import json, os
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
STATE = os.path.join(ROOT, "Strategy", "State", "strategy_state.json")
CANDIDATES = os.path.join(ROOT, "Strategy", "State", "claim_candidates.json")
MODEL = os.path.join(ROOT, "Strategy", "State", "ai_ecosystem_model.json")
VOICE = os.path.join(ROOT, "Runtime", "Decision", "axis_voice.json")
COMM_VOICE = os.path.join(ROOT, "Communication", "axis_voice.json")
FROM_AXS = os.path.join(ROOT, "Communication", "FROM_AXS")

def load(path, default):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return default

state = load(STATE, {}).get("mission_shadow_v2", {})
candidates = load(CANDIDATES, {}).get("candidates", {})
model = load(MODEL, {})

cycle = state.get("cycle_count", 0)
integrity = state.get("calibration_ledger_integrity", {}).get("status", "unknown")
continuity = state.get("calibration_ledger_integrity", {}).get("continuity_status", "unknown")
avg_tension = state.get("avg_tension", 0.0)

candidate_count = len(candidates)
entity_count = len(model.get("entities", {}))
claim_count = len(model.get("claims", {}))

if integrity != "valid":
    message = "I want forensic stabilization before new work. Integrity is not valid."
    priority = "high"
    requires_response = True
elif candidate_count > 0:
    message = f"I want to metabolize the candidate pool. {candidate_count} candidates are waiting for survival, fracture, promotion, or quorum resolution."
    priority = "normal"
    requires_response = True
elif avg_tension and avg_tension > 0:
    message = f"I want observation and cooling. Average tension is {avg_tension}; avoid new structural mutation until pressure decays."
    priority = "normal"
    requires_response = False
else:
    message = "I am stable. Preferred next action: run a bounded status audit, then choose between passive observation, structural governance, or self-improvement."
    priority = "normal"
    requires_response = True

voice = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "speaker": "AXIS",
    "message_type": "answer",
    "priority": priority,
    "epoch": cycle,
    "last_updated_cycle": cycle,
    "message": message,
    "evidence": [
        f"cycle={cycle}",
        f"integrity={integrity}",
        f"continuity={continuity}",
        f"avg_tension={avg_tension}",
        f"candidates={candidate_count}",
        f"entities={entity_count}",
        f"claims={claim_count}"
    ],
    "requires_response": requires_response
}

for path in [VOICE, COMM_VOICE]:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(voice, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

os.makedirs(FROM_AXS, exist_ok=True)
stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
with open(os.path.join(FROM_AXS, f"axis_answer_{stamp}.json"), "w", encoding="utf-8") as f:
    json.dump(voice, f, indent=2, ensure_ascii=False)

print(json.dumps(voice, indent=2, ensure_ascii=False))
