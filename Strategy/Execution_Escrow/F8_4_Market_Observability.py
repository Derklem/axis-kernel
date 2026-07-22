import json
import os
import datetime
from collections import defaultdict

MARKET_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_theory_market_v2.jsonl"
OBSERVATIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_observations.jsonl"
REJECTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_rejections.jsonl"
OVERRIDES_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_operational_overrides.jsonl"
REGISTRY_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\source_authority_registry.json"
PREDICTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_predictions.jsonl"
RESOLUTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_prediction_resolutions.jsonl"
CALIBRATION_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_theory_calibration.jsonl"

REPORT_MD_PATH = r"D:\Infinite\Infinity\Reports\F8_Market_Health_Report.md"
REPORT_JSON_PATH = r"D:\Infinite\Infinity\Telemetry\F8_Market_Health_Report.json"

def read_jsonl(path):
    data = []
    malformed = 0
    if not os.path.exists(path): return data, malformed
    with open(path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    data.append(json.loads(line))
                except Exception:
                    malformed += 1
    return data, malformed

def parse_ts(ts):
    if not ts:
        return None
    try:
        ts = ts.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone.utc)
    except Exception:
        return None

def generate_report():
    # 1. Load Data
    market, m_malf = read_jsonl(MARKET_PATH)
    obs, o_malf = read_jsonl(OBSERVATIONS_PATH)
    rejections, r_malf = read_jsonl(REJECTIONS_PATH)
    overrides, ov_malf = read_jsonl(OVERRIDES_PATH)
    predictions, p_malf = read_jsonl(PREDICTIONS_PATH)
    resolutions, res_malf = read_jsonl(RESOLUTIONS_PATH)
    calibrations, cal_malf = read_jsonl(CALIBRATION_PATH)
    
    ADJUSTMENTS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_calibration_adjustments.jsonl"
    adjustments, adj_malf = read_jsonl(ADJUSTMENTS_PATH)
    
    malformed_total = m_malf + o_malf + r_malf + ov_malf + p_malf + res_malf + cal_malf + adj_malf
    
    registry = {"sources": {}}
    if os.path.exists(REGISTRY_PATH):
        try:
            with open(REGISTRY_PATH, 'r') as f:
                registry = json.load(f)
        except: pass
        
    total_primary_weight = sum(o.get('evidence_weight', 1.0) for o in obs if not o.get('is_derived'))
    total_derived_weight = sum(a.get('evidence_weight', 1.0) for a in adjustments if a.get('is_derived'))
    total_weight = total_primary_weight + total_derived_weight
    
    derived_ratio = total_derived_weight / total_weight if total_weight > 0 else 0
    derived_to_primary = total_derived_weight / total_primary_weight if total_primary_weight > 0 else 0
    
    loop_capture_watch = derived_ratio >= 0.25
    loop_capture_risk = derived_ratio >= 0.40 or derived_to_primary >= 0.67
            
    # Time window analysis for stagnation
    last_activity = None
    all_events = obs + rejections + overrides
    if all_events:
        times = []
        for e in all_events:
            ts = e.get('timestamp_utc') or e.get('rejected_utc')
            parsed = parse_ts(ts)
            if parsed: times.append(parsed)
        if times:
            last_activity = max(times)
            
    stagnation_warning = False
    if last_activity:
        delta = datetime.datetime.now(datetime.timezone.utc) - last_activity
        if delta.total_seconds() > 3600: # 1 hour of silence
            stagnation_warning = True
    else:
        stagnation_warning = True

    # 2. Epistemic State
    groups = defaultdict(list)
    retired = []
    birth_required = []
    
    for m in market:
        groups[m['theory_group_id']].append(m)
        epistemic = m.get('epistemic_status', 'ACTIVE')
        if epistemic == 'RETIRED': retired.append(m)
        if epistemic == 'THEORY_BIRTH_REQUIRED': birth_required.append(m)
        
    normalization_passed = True
    normalization_errors = []
    
    group_distributions = {}
    for gid, theories in groups.items():
        active = [t for t in theories if t.get('epistemic_status', 'ACTIVE') != 'RETIRED']
        total_conf = sum(t.get('confidence_score', 0) for t in active)
        if active and not (0.99 <= total_conf <= 1.01):
            normalization_passed = False
            normalization_errors.append(f"{gid} sums to {total_conf:.4f}")
            
        group_distributions[gid] = {
            "total_active": len(active),
            "sum_confidence": round(total_conf, 4),
            "theories": [{"id": t['theory_id'], "conf": t.get('confidence_score', 0), "drift": round(t.get('confidence_score', 0) - 0.3333, 4)} for t in theories]
        }
        
    # 3. Authority State
    rejected_count = len(rejections)
    total_submissions = len(obs) + rejected_count
    
    rejection_reasons_by_source = defaultdict(lambda: defaultdict(int))
    for r in rejections:
        src = r.get('source', r.get('resolution_source', 'unknown'))
        reason = r.get('rejection_reason', 'unknown')
        rejection_reasons_by_source[src][reason] += 1
        
    # 4. Operational State
    active_overrides = []
    for m in market:
        if m.get('operational_status') == 'OPERATIONAL_OVERRIDE':
            reason = "Unknown"
            if m.get('history'):
                ov_events = [h for h in m['history'] if h.get('event') == 'OPERATIONAL_OVERRIDE']
                if ov_events: reason = ov_events[-1].get('reason', 'Unknown')
            active_overrides.append({"id": m['theory_id'], "reason": reason})

    # 5. Forecasting State
    resolved_pred_ids = {r.get('prediction_id') for r in resolutions if r.get('prediction_id')}
    resolved_count = len(resolutions)
    success_count = sum(1 for r in resolutions if r.get('success') is True)
    failure_count = sum(1 for r in resolutions if r.get('success') is False)

    open_predictions_by_theory = defaultdict(int)
    total_open_predictions = 0
    for p in predictions:
        theory_id = p.get("theory_id")
        if not theory_id:
            malformed_total += 1
            continue
        if p.get("prediction_id") not in resolved_pred_ids:
            open_predictions_by_theory[theory_id] += 1
            total_open_predictions += 1
            
    last_calibration_state = {}
    for c in calibrations:
        t_id = c.get('theory_id')
        if t_id:
            last_calibration_state[t_id] = c

    # Assemble JSON
    report = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "epistemic_state": {
            "group_distributions": group_distributions,
            "retired_theories": [{"id": t['theory_id'], "final_conf": t.get('confidence_score', 0)} for t in retired],
            "birth_required_groups": [{"id": t['theory_id']} for t in birth_required]
        },
        "authority_state": {
            "source_trust_scores": {k: v.get('trust_score', 1.0) for k,v in registry.get('sources', {}).items()},
            "total_submissions": total_submissions,
            "rejected_count": rejected_count,
            "rejection_rate": round(rejected_count / max(total_submissions, 1), 4),
            "rejection_reasons_by_source": {k: dict(v) for k,v in rejection_reasons_by_source.items()}
        },
        "operational_state": {
            "active_overrides": active_overrides
        },
        "forecasting_state": {
            "open_predictions_by_theory": dict(open_predictions_by_theory),
            "total_open_predictions": total_open_predictions,
            "total_resolved": resolved_count,
            "successful_resolutions": success_count,
            "failed_resolutions": failure_count,
            "calibration_state": last_calibration_state
        },
        "integrity_state": {
            "normalization_passed": normalization_passed,
            "normalization_errors": normalization_errors,
            "malformed_ledger_rows": malformed_total,
            "market_stagnation_warning": stagnation_warning,
            "total_primary_weight": total_primary_weight,
            "total_derived_weight": total_derived_weight,
            "loop_capture_watch": loop_capture_watch,
            "loop_capture_risk": loop_capture_risk
        }
    }
    
    # Save JSON
    os.makedirs(os.path.dirname(REPORT_JSON_PATH), exist_ok=True)
    with open(REPORT_JSON_PATH, 'w', encoding="utf-8") as f:
        json.dump(report, f, indent=4)
        
    # Assemble Markdown
    md = [
        "# F8 Market Health Report",
        f"**Generated:** {report['timestamp_utc']}",
        "",
        "## Integrity State",
        f"- **Normalization Check:** {'PASSED' if normalization_passed else 'FAILED'}"
    ]
    if not normalization_passed:
        for err in normalization_errors: md.append(f"  - {err}")
    md.append(f"- **Malformed Ledger Rows:** {malformed_total}")
    
    md.append("\n## Loop Integrity")
    md.append(f"- **Primary Evidence Weight:** {total_primary_weight:.4f}")
    md.append(f"- **Derived Evidence Weight:** {total_derived_weight:.4f}")
    if loop_capture_risk:
        md.append("- **[WARNING] LOOP_CAPTURE_RISK:** Derivative evidence dominates primary evidence.")
    elif loop_capture_watch:
        md.append("- **[WATCH] LOOP_CAPTURE_WATCH:** Derivative evidence is becoming influential.")
    else:
        md.append("- **Status:** NOMINAL")

    if stagnation_warning:
        md.append("- **[WARNING] MARKET_STAGNATION_RISK:** No recent activity detected.")
        
    md.append("\n## Epistemic State")
    for gid, data in group_distributions.items():
        md.append(f"### {gid} (Sum Conf: {data['sum_confidence']})")
        for t in data['theories']:
            md.append(f"- {t['id']}: {t['conf']:.4f} (Drift: {t['drift']:+.4f})")
            
    md.append("\n### Retired Theories Graveyard")
    if not retired: md.append("- None")
    for r in retired: md.append(f"- {r['theory_id']} (Final Conf: {r.get('final_conf', r.get('confidence_score', 0)):.4f})")
    
    md.append("\n### Birth-Required Anomalies")
    if not birth_required: md.append("- None")
    for b in birth_required: md.append(f"- {b['theory_id']} (Unknown dominance)")
    
    md.append("\n## Authority State")
    md.append(f"- **Total Submissions:** {total_submissions}")
    md.append(f"- **Rejected Events:** {rejected_count} ({report['authority_state']['rejection_rate']:.2%})")
    md.append("\n### Source Trust Scores")
    for src, score in report['authority_state']['source_trust_scores'].items():
        md.append(f"- {src}: {score:.4f}")
        
    md.append("\n### Rejections by Source")
    if not rejection_reasons_by_source: md.append("- None")
    for src, reasons in rejection_reasons_by_source.items():
        md.append(f"**{src}**:")
        for reason, count in reasons.items():
            md.append(f"- {reason} ({count} times)")
            
    md.append("\n## Operational State")
    md.append("### Active Overrides")
    if not active_overrides: md.append("- None")
    for ov in active_overrides:
        md.append(f"- {ov['id']}: {ov['reason']}")
        
    md.append("\n## Forecasting State")
    md.append(f"- **Total Open Predictions:** {total_open_predictions}")
    md.append(f"- **Resolved Predictions:** {resolved_count} ({success_count} success, {failure_count} fail)")
    md.append("\n### Open Predictions by Theory")
    if not open_predictions_by_theory:
        md.append("- No open predictions.")
    else:
        for t_id, count in sorted(open_predictions_by_theory.items()):
            if count > 0:
                md.append(f"- **{t_id}**: {count} open predictions")

    md.append("\n### Theory Calibration State")
    if not last_calibration_state:
        md.append("- No theories calibrated.")
    else:
        for t_id, c in sorted(last_calibration_state.items()):
            st = c.get('calibration_state', 'UNPROVEN')
            acc = c.get('forecast_accuracy', 0.0) * 100
            res = c.get('resolved_predictions', 0)
            md.append(f"- **{t_id}**: {st} ({res} resolved, {acc:.1f}% accuracy)")
        
    md_text = "\n".join(md)
    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)
    with open(REPORT_MD_PATH, 'w', encoding="utf-8") as f:
        f.write(md_text)
        
    try:
        print(md_text)
    except Exception:
        print(md_text.encode('utf-8', 'replace').decode('utf-8'))
    print(f"\n[Artifacts exported to {REPORT_MD_PATH} and {REPORT_JSON_PATH}]")

if __name__ == "__main__":
    generate_report()
