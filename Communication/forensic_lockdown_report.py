import os, sys, json
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
STRATEGY = os.path.join(ROOT, "Strategy")
STATE = os.path.join(STRATEGY, "State")
VOICE = os.path.join(ROOT, "Runtime", "Decision", "axis_voice.json")
REPORT_DIR = os.path.join(ROOT, "Communication", "FROM_AXS")
os.makedirs(REPORT_DIR, exist_ok=True)

STATE_FILE = os.path.join(STATE, "strategy_state.json")
CAND_FILE = os.path.join(STATE, "claim_candidates.json")
MODEL_FILE = os.path.join(STATE, "ai_ecosystem_model.json")

sys.path.append(STRATEGY)
from strategy_engine import StrategyEngine

e = StrategyEngine()
ledger = e._load_shadow_ledger()
integrity = ledger.get("calibration_ledger_integrity", {})

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as ex:
        return {"error": str(ex), **default}

candidates = load_json(CAND_FILE, {"candidates": {}})
model = load_json(MODEL_FILE, {"entities": {}, "claims": {}})

candidate_map = candidates.get("candidates", {})
directive_candidates = []
for k, v in candidate_map.items():
    blob = json.dumps(v, ensure_ascii=False)
    if "USER_DIRECTIVE" in blob or "sovereign_intent" in blob or "USER_VOICE" in blob:
        directive_candidates.append({
            "id": k,
            "entity": v.get("entity"),
            "claim_domain": v.get("claim_domain"),
            "source_id": v.get("source_id"),
            "source_type": v.get("source_type"),
            "artifact_type": v.get("artifact_type"),
            "confidence": v.get("confidence"),
            "cycles_survived": v.get("cycles_survived"),
            "claim_preview": str(v.get("claim", ""))[:240]
        })

report = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "speaker": "AXIS",
    "message_type": "forensic_lockdown_report",
    "priority": "high",
    "epoch": ledger.get("cycle_count"),
    "message": "Read-only lockdown report complete. Witness is synchronized, but governance integrity remains in continuity_violation/broken posture.",
    "ledger": {
        "cycle_count": ledger.get("cycle_count"),
        "integrity_status": integrity.get("status"),
        "continuity_status": integrity.get("continuity_status"),
        "break_reason": integrity.get("break_reason"),
        "broken_witness_log_hash": integrity.get("broken_witness_log_hash"),
        "last_verified_cycle": integrity.get("last_verified_cycle"),
        "witness_chain_head": str(ledger.get("witness_chain_head"))[:16],
        "ecosystem_receipts_head": str(ledger.get("ecosystem_receipts_head"))[:16],
        "avg_tension": ledger.get("avg_tension"),
        "horizon_tension_score": ledger.get("horizon_tension_score"),
        "idle_cycles": ledger.get("idle_cycles"),
        "outcome_history_tail": ledger.get("outcome_history", [])[-5:]
    },
    "candidate_pool": {
        "count": len(candidate_map),
        "directive_candidates": directive_candidates
    },
    "model": {
        "entity_count": len(model.get("entities", {})),
        "claim_count": len(model.get("claims", {})),
        "cycle_count": model.get("cycle_count")
    },
    "recommendation": (
        "Do not run cycles. Do not re-enable self-improvement. "
        "If directive_candidates exist, archive/quarantine them before any re-anchor. "
        "If no directive candidates exist and only integrity flags remain broken, perform formal forensic re-anchor."
    ),
    "actual_mutation_authorized": False,
    "requires_response": True
}

stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
path = os.path.join(REPORT_DIR, f"forensic_lockdown_report_{stamp}.json")

with open(path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

tmp = VOICE + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
os.replace(tmp, VOICE)

print(json.dumps(report, indent=2, ensure_ascii=False))
print("REPORT:", path)
