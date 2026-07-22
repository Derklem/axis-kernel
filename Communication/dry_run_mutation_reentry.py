import os, sys, json
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
STRATEGY = os.path.join(ROOT, "Strategy")
VOICE = os.path.join(ROOT, "Runtime", "Decision", "axis_voice.json")
REPORT_DIR = os.path.join(ROOT, "Communication", "FROM_AXS")
os.makedirs(REPORT_DIR, exist_ok=True)

sys.path.append(STRATEGY)
from strategy_engine import StrategyEngine

e = StrategyEngine()
ledger = e._load_shadow_ledger()
integrity = ledger.get("calibration_ledger_integrity", {})

cycle = ledger.get("cycle_count", 0)
status = integrity.get("status", "unknown")
continuity = integrity.get("continuity_status", "unknown")
witness = ledger.get("witness_chain_head", "none")
receipts = ledger.get("ecosystem_receipts_head", "none")
avg_tension = ledger.get("avg_tension", None)
horizon_tension = ledger.get("horizon_tension_score", None)
turbulence = ledger.get("predictive_turbulence", {})
bias_gate = ledger.get("bias_calibration_gate", {})
candidates = {}

try:
    candidates = e.ecosystem_mapper._load_candidates().get("candidates", {})
except Exception:
    candidates = {}

si_enabled = os.getenv("AXIS_SELF_IMPROVEMENT_ENABLED", "0")

conditions = {
    "integrity_valid": status == "valid",
    "continuity_intact": continuity == "intact",
    "witness_present": witness not in ("none", "", None),
    "self_improvement_enabled": si_enabled == "1",
    "candidate_pool_empty": len(candidates) == 0,
    "avg_tension_low": (avg_tension is not None and avg_tension < 0.15),
    "horizon_tension_zero": horizon_tension == 0.0,
    "predictive_caution_inactive": turbulence.get("caution_active") is False,
    "bias_gate_closed": bias_gate.get("status") == "closed"
}

blockers = []
if not conditions["integrity_valid"]:
    blockers.append("integrity_not_valid")
if not conditions["continuity_intact"]:
    blockers.append("continuity_not_intact")
if not conditions["witness_present"]:
    blockers.append("witness_missing")
if not conditions["self_improvement_enabled"]:
    blockers.append("self_improvement_flag_disabled")
if not conditions["avg_tension_low"]:
    blockers.append("avg_tension_not_low")
if not conditions["predictive_caution_inactive"]:
    blockers.append("predictive_caution_active")

# Dry-run decision: do NOT authorize actual mutation.
would_allow_mutation_if_live = (
    conditions["integrity_valid"]
    and conditions["continuity_intact"]
    and conditions["witness_present"]
    and conditions["self_improvement_enabled"]
    and conditions["avg_tension_low"]
    and conditions["predictive_caution_inactive"]
)

result = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "speaker": "AXIS",
    "message_type": "dry_run_mutation_reentry",
    "priority": "high" if blockers else "normal",
    "epoch": cycle,
    "last_updated_cycle": cycle,
    "message": (
        "Dry-run mutation re-entry simulation complete. "
        + ("Mutation remains blocked in live posture." if blockers else "All inspected gates would pass, but this was read-only and no mutation was authorized.")
    ),
    "diagnostics": {
        "cycle": cycle,
        "integrity": status,
        "continuity": continuity,
        "witness_head": witness[:16],
        "ecosystem_receipts_head": receipts[:16],
        "avg_tension": avg_tension,
        "horizon_tension": horizon_tension,
        "candidate_count": len(candidates),
        "self_improvement_flag": si_enabled,
        "predictive_turbulence": turbulence,
        "bias_calibration_gate": bias_gate
    },
    "conditions": conditions,
    "blockers": blockers,
    "would_allow_mutation_if_live": would_allow_mutation_if_live,
    "actual_mutation_authorized": False,
    "requires_response": True
}

stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
report_path = os.path.join(REPORT_DIR, f"dry_run_mutation_reentry_{stamp}.json")

with open(report_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

tmp = VOICE + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
os.replace(tmp, VOICE)

print(json.dumps(result, indent=2, ensure_ascii=False))
print("REPORT:", report_path)
