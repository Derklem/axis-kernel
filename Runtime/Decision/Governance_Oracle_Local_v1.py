import os
import sys
import json
import time
import hashlib
from datetime import datetime, timezone

BASELINE_METADATA_FILE = r"D:\Infinite\Infinity\Strategy\Proposals\Bridge_Baseline_Metadata.json"
BASELINE_HASHES = {}
if os.path.exists(BASELINE_METADATA_FILE):
    try:
        with open(BASELINE_METADATA_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
            BASELINE_HASHES = meta.get("hashes", {})
    except Exception as e:
        print(f"Warning: Could not read Bridge_Baseline_Metadata.json: {e}")

STATE_FILE = r"D:\Infinite\Infinity\Strategy\State\strategy_state.json"
ANCHOR_FILE = r"D:\Infinite\Infinity\Strategy\State\calibration_continuity_anchor.json"
WITNESS_LEDGER = r"D:\Infinite\Infinity\Strategy\State\forensic_witness_ledger.jsonl"
AGENT_PROPOSALS = r"D:\Infinite\Infinity\Strategy\Proposals\Agent_Proposals.jsonl"
METRICS_OUT = r"D:\Infinite\Infinity\Runtime\Decision\Governance_Metrics.json"

def get_hash(path):
    if not os.path.exists(path): return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def observe_local_system():
    stability_index = 100.0
    anomalies = []
    
    # 1. State/Anchor Consistency & Hash Drift
    state_hash = get_hash(STATE_FILE)
    anchor_hash = get_hash(ANCHOR_FILE)
    
    expected_state = BASELINE_HASHES.get("strategy_state.json")
    expected_anchor = BASELINE_HASHES.get("calibration_continuity_anchor.json")
    
    if not state_hash:
        stability_index -= 20.0
        anomalies.append("strategy_state_missing")
    elif state_hash != expected_state:
        stability_index -= 10.0
        anomalies.append("strategy_state_hash_drift")
        
    if not anchor_hash:
        stability_index -= 20.0
        anomalies.append("anchor_missing")
    elif anchor_hash != expected_anchor:
        stability_index -= 10.0
        anomalies.append("anchor_hash_drift")
        
    # 2. Witness Ledger Tail Freshness & Parseability
    witness_parseable = False
    witness_tail_accessible = False
    last_witness_age_seconds = -1
    
    if os.path.exists(WITNESS_LEDGER):
        try:
            with open(WITNESS_LEDGER, "r") as f:
                lines = f.readlines()
            if lines:
                witness_tail_accessible = True
                last_line = lines[-1]
                try:
                    record = json.loads(last_line)
                    witness_parseable = True
                    # Check age
                    ts_str = record.get("ts_utc")
                    if ts_str:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        last_witness_age_seconds = (datetime.now(timezone.utc) - ts).total_seconds()
                except Exception as e:
                    stability_index -= 15.0
                    anomalies.append("witness_ledger_tail_corrupt")
        except:
            stability_index -= 15.0
            anomalies.append("witness_ledger_unreadable")
    else:
        stability_index -= 20.0
        anomalies.append("witness_ledger_missing")
        
    if last_witness_age_seconds > 86400: # Older than 24h
        stability_index -= 5.0
        anomalies.append("witness_ledger_stale")
        
    # 3. Pending Proposal Count
    pending_count = 0
    if os.path.exists(AGENT_PROPOSALS):
        try:
            with open(AGENT_PROPOSALS, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            prop = json.loads(line)
                            if prop.get("status") == "PENDING":
                                pending_count += 1
                        except:
                            pass
        except:
            pass
            
    if pending_count > 5:
        stability_index -= 5.0
        anomalies.append("high_pending_proposal_queue")

    return {
        "stability_index": max(0.0, round(stability_index, 2)),
        "anomalies": anomalies,
        "witness_parseable": witness_parseable,
        "witness_tail_accessible": witness_tail_accessible,
        "last_witness_age_seconds": round(last_witness_age_seconds, 1) if last_witness_age_seconds >= 0 else None,
        "pending_proposals": pending_count
    }

def main():
    obs = observe_local_system()
    
    # Tier 1 Oracle determines health solely based on local observability limits
    metrics_health = "degraded"
    
    # Read Executor State Telemetry
    executor_state_file = r"D:\Infinite\Infinity\Runtime\Executor\executor_state.json"
    executor_last_run_fault = 0
    if os.path.exists(executor_state_file):
        try:
            with open(executor_state_file, "r", encoding="utf-8") as f:
                exec_state = json.load(f)
                executor_last_run_fault = exec_state.get("error_count_last_hour", 0)
        except:
            executor_last_run_fault = 0
            
    # Read Executor Fault Ledger for 24h circuit trips
    ledger_file = r"D:\Infinite\Infinity\Runtime\Executor\executor_fault_ledger.jsonl"
    circuit_trips_24h = 0
    ledger_provenance = "unobserved_conservative_fallback"
    circuit_trips_val = 999
    
    if os.path.exists(ledger_file):
        try:
            now_utc = datetime.now(timezone.utc)
            faults = 0
            with open(ledger_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        record = json.loads(line)
                        if record.get("drill") is True: continue
                        ts_str = record.get("timestamp_utc")
                        if not ts_str: continue
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if (now_utc - ts).total_seconds() <= 86400:
                            if record.get("fault") is True:
                                faults += 1
                    except:
                        pass
            circuit_trips_val = faults
            ledger_provenance = "observed_from_executor_fault_ledger"
        except:
            pass

    # Read Watchdog Ledger for last hour restarts
    watchdog_ledger = r"D:\Infinite\Infinity\Runtime\Watchdog\watchdog_ledger.jsonl"
    watchdog_restarts_1h = 999
    watchdog_provenance = "unobserved_conservative_fallback"
    
    if os.path.exists(watchdog_ledger):
        try:
            now_utc = datetime.now(timezone.utc)
            restarts = 0
            with open(watchdog_ledger, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        record = json.loads(line)
                        if record.get("drill") is True: continue
                        ts_str = record.get("timestamp_utc")
                        if not ts_str: continue
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if (now_utc - ts).total_seconds() <= 3600:
                            if record.get("restart_attempted") is True:
                                restarts += 1
                    except:
                        pass
            watchdog_restarts_1h = restarts
            watchdog_provenance = "observed_from_watchdog_ledger"
        except:
            pass

    # Read Incident Ledger for MTTR (95th percentile, last 24h)
    incident_ledger = r"D:\Infinite\Infinity\Runtime\Telemetry\incident_snapshot.jsonl"
    mttr_val = 999
    mttr_provenance = "insufficient_incident_samples_conservative_fallback"
    
    if os.path.exists(incident_ledger):
        try:
            now_utc = datetime.now(timezone.utc)
            durations = []
            with open(incident_ledger, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        record = json.loads(line)
                        if record.get("status") != "resolved": continue
                        if record.get("drill") is True: continue
                        
                        ts_str = record.get("recovery_timestamp_utc")
                        if not ts_str: continue
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00").replace("ZZ", "Z"))
                        
                        if (now_utc - ts).total_seconds() <= 86400:
                            dur = record.get("duration_seconds")
                            if dur is not None:
                                durations.append(dur)
                    except:
                        pass
            
            if len(durations) > 0:
                durations.sort()
                # Calculate 95th percentile manually
                import math
                idx = math.ceil(0.95 * len(durations)) - 1
                mttr_val = round(durations[idx], 2)
                mttr_provenance = "observed_from_incident_ledger"
        except:
            pass

    # Read Execution Verification Ledger for Phase E metrics
    verification_ledger = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\execution_verification.jsonl"
    execution_verifications_last_24h = 0
    execution_verification_failures_last_24h = 0
    last_execution_verification_status = "insufficient_samples"
    execution_verification_provenance = "observed_from_execution_verification_ledger"
    
    if os.path.exists(verification_ledger):
        try:
            now_utc = datetime.now(timezone.utc)
            with open(verification_ledger, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    try:
                        record = json.loads(line)
                        if record.get("drill") is True: continue
                        ts_str = record.get("verified_utc")
                        if not ts_str: continue
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        
                        if (now_utc - ts).total_seconds() <= 86400:
                            execution_verifications_last_24h += 1
                            if record.get("verified") is False:
                                execution_verification_failures_last_24h += 1
                                
                        # Update last status
                        if record.get("verified") is True:
                            last_execution_verification_status = "verified_ok"
                        else:
                            if record.get("file_exists") is False:
                                last_execution_verification_status = "failed_missing"
                            else:
                                last_execution_verification_status = "failed_hash_mismatch"
                    except:
                        pass
        except:
            pass

    # Calculate Substrate Drift KB
    substrate_drift_kb = 0.0
    file_map = {
        "strategy_state.json": STATE_FILE,
        "calibration_continuity_anchor.json": ANCHOR_FILE,
        "forensic_witness_ledger.jsonl": WITNESS_LEDGER
    }
    
    for fname, expected_hash in BASELINE_HASHES.items():
        if fname in file_map:
            path = file_map[fname]
            current_hash = get_hash(path)
            if current_hash != expected_hash:
                try:
                    size_bytes = os.path.getsize(path)
                    substrate_drift_kb += size_bytes / 1024.0
                except:
                    pass
                    
    substrate_drift_kb = round(substrate_drift_kb, 2)

    metrics = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "metrics_health": metrics_health,
        "approval_capable": False,
        "oracle_confidence": "local_partial",
        
        "stability_index": obs["stability_index"],
        "stability_index_provenance": "tier_1_local_observation",
        
        "executor_last_run_fault": executor_last_run_fault,
        "executor_last_run_fault_provenance": "observed_from_T08_executor_state",
        
        "circuit_trips_last_24h": circuit_trips_val,
        "circuit_trips_last_24h_provenance": ledger_provenance,
        "watchdog_restarts_last_hour": watchdog_restarts_1h,
        "watchdog_restarts_last_hour_provenance": watchdog_provenance,
        "mttr_p95_24h": mttr_val,
        "mttr_p95_24h_provenance": mttr_provenance,
        "substrate_drift_kb": substrate_drift_kb,
        "substrate_drift_kb_provenance": "observed_from_baseline_hash_drift",
        "substrate_drift_semantics": "tracked_file_hash_drift_kb_not_memory_drift",
        
        "execution_verifications_last_24h": execution_verifications_last_24h,
        "execution_verification_failures_last_24h": execution_verification_failures_last_24h,
        "last_execution_verification_status": last_execution_verification_status,
        "execution_verification_provenance": execution_verification_provenance,
        
        "oracle_limits": {
            "mttr_p95_24h": "insufficient_resolved_incident_samples",
            "meaning": "Most Tier 2 local metrics are observed; MTTR remains conservative until resolved incidents exist."
        },
        
        # Local Observational Telemetry extension
        "tier_1_telemetry": {
            "witness_ledger_parseable": obs["witness_parseable"],
            "witness_tail_accessible": obs["witness_tail_accessible"],
            "last_witness_timestamp_age_seconds": obs["last_witness_age_seconds"],
            "pending_proposals": obs["pending_proposals"],
            "detected_anomalies": obs["anomalies"]
        }
    }
    
    os.makedirs(os.path.dirname(METRICS_OUT), exist_ok=True)
    with open(METRICS_OUT, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
        
    print(f"Tier 1 Governance Oracle executed.")
    print(f"Metrics written to {METRICS_OUT}")
    print(f"Stability Index: {obs['stability_index']}")
    print(f"Health: {metrics_health} | Approval Capable: {metrics['approval_capable']}")
    if obs['anomalies']:
        print(f"Anomalies: {', '.join(obs['anomalies'])}")

if __name__ == "__main__":
    main()
