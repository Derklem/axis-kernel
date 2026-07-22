import os
import json
import datetime
from collections import defaultdict

ESCROW_DIR = r"D:\Infinite\Infinity\Strategy\Execution_Escrow"
RECEIPTS_FILE = os.path.join(ESCROW_DIR, "execution_receipts.jsonl")
DENIALS_FILE = os.path.join(ESCROW_DIR, "execution_denials.jsonl")
LEDGER_PATH = r"D:\Infinite\Infinity\Telemetry\Verification_History_Ledger.jsonl"
PRESSURE_LEDGER_PATH = r"D:\Infinite\Infinity\Telemetry\Trust_Pressure_Ledger.jsonl"
REPORT_PATH = r"D:\Infinite\Infinity\Reports\Axis_Operational_Summary.md"

# Re-use aggregator logic for historical replay
def calculate_success_rate(entries, window_size):
    if not entries: return 1.0
    recent = entries[-window_size:]
    success_count = sum(1 for e in recent if e.get("verification_outcome") == "success")
    return success_count / len(recent)

def calculate_consecutive_failures(entries):
    count = 0
    for e in reversed(entries):
        if e.get("verification_outcome") != "success": count += 1
        else: break
    return count

def get_pressure_for_entries(entries):
    last_20 = calculate_success_rate(entries, 20)
    last_50 = calculate_success_rate(entries, 50)
    last_100 = calculate_success_rate(entries, 100)
    consecutive_failures = calculate_consecutive_failures(entries)

    freeze_rec = consecutive_failures >= 3
    block_rec = last_100 < 0.85
    human_rec = last_50 < 0.90
    scrutiny_rec = last_20 < 0.95

    if freeze_rec: return "execution_freeze_recommended"
    elif block_rec: return "block_execution_capable_recommended"
    elif human_rec: return "human_review_recommended"
    elif scrutiny_rec: return "increased_scrutiny_recommended"
    else: return "normal"

def parse_iso(ts_str):
    try:
        return datetime.datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
    except:
        return datetime.datetime.utcnow()

def main():
    # Organic counts
    org_executions = 0
    org_denials = 0
    org_denial_reasons = defaultdict(int)
    
    # Drill counts
    drill_executions = 0
    drill_denials = 0
    drill_denial_reasons = defaultdict(int)
    
    # F6 Defense Scoring
    SCORES_FILE = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_defense_scores.jsonl"
    latest_defense_quality_score = None
    defense_scores_non_drill = []
    incomplete_defenses_non_drill = 0
    low_quality_defenses_non_drill = 0
    missing_sections_frequency = defaultdict(int)
    scores_7d_non_drill = []
    scores_30d_non_drill = []

    # 1. Total Executions
    if os.path.exists(RECEIPTS_FILE):
        with open(RECEIPTS_FILE, 'r') as f:
            for line in f:
                if not line.strip(): continue
                try:
                    r = json.loads(line)
                    if r.get("drill") is True:
                        drill_executions += 1
                    else:
                        org_executions += 1
                except:
                    pass

    # 2. Denials
    if os.path.exists(DENIALS_FILE):
        with open(DENIALS_FILE, 'r') as f:
            for line in f:
                if not line.strip(): continue
                try:
                    d = json.loads(line)
                    reason = d.get("reason", "unknown")
                    if d.get("drill") is True:
                        drill_denials += 1
                        drill_denial_reasons[reason] += 1
                    else:
                        org_denials += 1
                        org_denial_reasons[reason] += 1
                except:
                    pass

    # 2b. Defense Scores (F6)
    if os.path.exists(SCORES_FILE):
        now = datetime.datetime.utcnow()
        with open(SCORES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    s = json.loads(line)
                    score = s.get("defense_quality_score", 0.0)
                    latest_defense_quality_score = score
                    
                    if s.get("drill") is not True:
                        defense_scores_non_drill.append(score)
                        
                        if score < 1.0:
                            incomplete_defenses_non_drill += 1
                        if score < 0.5:
                            low_quality_defenses_non_drill += 1
                            
                        for ms in s.get("missing_sections", []):
                            missing_sections_frequency[ms] += 1
                            
                        ts_str = s.get("timestamp_utc")
                        if ts_str:
                            try:
                                entry_ts = datetime.datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
                                age_days = (now - entry_ts).total_seconds() / 86400.0
                                if age_days <= 7:
                                    scores_7d_non_drill.append(score)
                                if age_days <= 30:
                                    scores_30d_non_drill.append(score)
                            except: pass
                except: pass
                
    # 3. Verifications (Historical Replay)
    non_drill_entries = []
    total_failures = 0
    historical_transitions = 0
    historical_time_spent = defaultdict(float) # seconds
    
    drill_verifications = 0
    
    current_pressure = "normal"
    last_ts = None
    
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, 'r') as f:
            for line in f:
                if not line.strip(): continue
                try:
                    entry = json.loads(line)
                    if entry.get("drill") is True:
                        drill_verifications += 1
                        continue
                        
                    ts = parse_iso(entry.get("timestamp", ""))
                    if last_ts is not None:
                        duration = (ts - last_ts).total_seconds()
                        if duration > 0:
                            historical_time_spent[current_pressure] += duration
                            
                    non_drill_entries.append(entry)
                    if entry.get("verification_outcome") != "success":
                        total_failures += 1
                        
                    new_pressure = get_pressure_for_entries(non_drill_entries)
                    if new_pressure != current_pressure:
                        historical_transitions += 1
                        current_pressure = new_pressure
                    last_ts = ts
                except:
                    pass
                    
    # Add time from last event until now
    if last_ts is not None:
        duration = (datetime.datetime.utcnow() - last_ts).total_seconds()
        if duration > 0:
            historical_time_spent[current_pressure] += duration
            
    # 4. Observed Ledger (Forward Observation)
    observed_transitions = 0
    observed_time_spent = defaultdict(float)
    obs_current = "normal"
    obs_last_ts = None
    
    if os.path.exists(PRESSURE_LEDGER_PATH):
        with open(PRESSURE_LEDGER_PATH, 'r') as f:
            for line in f:
                if not line.strip(): continue
                try:
                    entry = json.loads(line)
                    ts = parse_iso(entry.get("timestamp_utc", ""))
                    if obs_last_ts is not None:
                        duration = (ts - obs_last_ts).total_seconds()
                        if duration > 0:
                            observed_time_spent[obs_current] += duration
                            
                    obs_current = entry.get("trust_pressure", "normal")
                    if entry.get("changed") is True:
                        observed_transitions += 1
                    obs_last_ts = ts
                except:
                    pass
                    
    if obs_last_ts is not None:
        duration = (datetime.datetime.utcnow() - obs_last_ts).total_seconds()
        if duration > 0:
            observed_time_spent[obs_current] += duration

    # 5. Format Report
    report = [
        "# Axis Operational Summary (Phase F4)",
        f"**Generated:** {datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}\n",
        "## Organic Baseline",
        f"- **Total Executions (Receipts):** {org_executions}",
        f"- **Total Verifications (Non-Drill):** {len(non_drill_entries)}",
        f"- **Total Failures (Non-Drill):** {total_failures}",
        f"- **Total Denial Events:** {org_denials}"
    ]
    
    if org_denial_reasons:
        report.append("  - Denial Reasons:")
        for r, c in org_denial_reasons.items():
            report.append(f"    - `{r}`: {c}")
            
    report.append("\n## Historical Test Artifacts (Drill Machinery)")
    report.append(f"- **Drill Executions:** {drill_executions}")
    report.append(f"- **Drill Verifications:** {drill_verifications}")
    report.append(f"- **Drill Denials:** {drill_denials}")
    if drill_denial_reasons:
        report.append("  - Drill Denial Reasons:")
        for r, c in drill_denial_reasons.items():
            report.append(f"    - `{r}`: {c}")
            
    report.append("\n## Trust Pressure Telemetry")
    report.append("### F4A: Historical Replay (Baseline Reconstruction)")
    report.append(f"- **Total Transitions:** {historical_transitions}")
    report.append("- **Time Spent:**")
    for state, secs in sorted(historical_time_spent.items(), key=lambda x: x[1], reverse=True):
        report.append(f"  - `{state}`: {secs/60.0:.1f} minutes")
        
    report.append("\n### F4B: Observed Ledger (Forward Observation)")
    report.append(f"- **Total Transitions:** {observed_transitions}")
    report.append("- **Time Spent:**")
    for state, secs in sorted(observed_time_spent.items(), key=lambda x: x[1], reverse=True):
        report.append(f"  - `{state}`: {secs/60.0:.1f} minutes")
        
    # Check divergence
    divergent = historical_transitions != observed_transitions
    report.append(f"\n### Divergence Check")
    if historical_transitions == 0 and observed_transitions == 1 and obs_current == "normal":
        report.append("**STATUS:** Expected initialization divergence. Forward ledger seeded its baseline.")
    elif divergent:
        report.append("**STATUS:** Divergence Detected between Historical Replay and Observed Ledger. This indicates interpretation rules or script logic changed over time.")
    else:
        report.append("**STATUS:** Clean. Historical replay matches observed ledger transitions.")
        
    report.append("\n## Phase F6: Defense Quality (ADVISORY ONLY)")
    report.append(f"- **Latest Defense Score:** {latest_defense_quality_score if latest_defense_quality_score is not None else 'N/A'}")
    if defense_scores_non_drill:
        avg_score = sum(defense_scores_non_drill) / len(defense_scores_non_drill)
        report.append(f"- **Average Score (Non-Drill):** {avg_score:.2f}")
    else:
        report.append(f"- **Average Score (Non-Drill):** N/A")
        
    report.append(f"- **Incomplete Defenses (Non-Drill):** {incomplete_defenses_non_drill}")
    report.append(f"- **Low Quality Defenses (Non-Drill):** {low_quality_defenses_non_drill}")
    
    if scores_7d_non_drill:
        avg_7d = sum(scores_7d_non_drill) / len(scores_7d_non_drill)
        report.append(f"- **7-Day Trend (Average):** {avg_7d:.2f}")
    else:
        avg_7d = None
        report.append(f"- **7-Day Trend (Average):** N/A")
        
    if scores_30d_non_drill:
        avg_30d = sum(scores_30d_non_drill) / len(scores_30d_non_drill)
        report.append(f"- **30-Day Trend (Average):** {avg_30d:.2f}")
    else:
        avg_30d = None
        report.append(f"- **30-Day Trend (Average):** N/A")
        
    if avg_7d is not None and avg_30d is not None:
        report.append(f"- **Improvement Rate (7d vs 30d):** {avg_7d - avg_30d:+.2f}")
    else:
        report.append(f"- **Improvement Rate (7d vs 30d):** N/A")
        
    if missing_sections_frequency:
        report.append("- **Missing Sections Frequency:**")
        for s, c in sorted(missing_sections_frequency.items(), key=lambda x: x[1], reverse=True):
            report.append(f"  - `{s}`: {c}")
        
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
        
    print(f"Operational Summary generated at {REPORT_PATH}")

if __name__ == '__main__':
    main()
