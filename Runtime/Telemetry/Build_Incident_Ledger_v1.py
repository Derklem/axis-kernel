import os
import json
import uuid
from datetime import datetime, timezone

EXECUTOR_LEDGER = r"D:\Infinite\Infinity\Runtime\Executor\executor_fault_ledger.jsonl"
WATCHDOG_LEDGER = r"D:\Infinite\Infinity\Runtime\Watchdog\watchdog_ledger.jsonl"
INCIDENT_LEDGER = r"D:\Infinite\Infinity\Runtime\Telemetry\incident_snapshot.jsonl"

def parse_iso(ts_str):
    if ts_str.endswith("ZZ"):
        ts_str = ts_str[:-2] + "Z"
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    return datetime.fromisoformat(ts_str)

def load_ledger(path, source_name):
    records = []
    if not os.path.exists(path):
        return records
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try:
                rec = json.loads(line)
                rec["_source_ledger"] = source_name
                records.append(rec)
            except:
                pass
    return records

def build_incident_ledger():
    exec_records = load_ledger(EXECUTOR_LEDGER, "executor_fault_ledger")
    wd_records = load_ledger(WATCHDOG_LEDGER, "watchdog_ledger")
    
    all_records = exec_records + wd_records
    all_records.sort(key=lambda x: parse_iso(x["timestamp_utc"]))
    
    incidents = []
    open_incident = None
    
    for rec in all_records:
        ts_utc = rec["timestamp_utc"]
        
        # Check if we should open an incident
        if open_incident is None:
            is_fault = False
            fault_type = ""
            
            if rec["_source_ledger"] == "executor_fault_ledger" and rec.get("fault") is True:
                is_fault = True
                fault_type = "executor_fault"
            elif rec["_source_ledger"] == "watchdog_ledger" and rec.get("restart_attempted") is True:
                is_fault = True
                fault_type = "watchdog_restart"
                
            if is_fault:
                open_incident = {
                    "incident_id": f"INC-{uuid.uuid4().hex[:8].upper()}",
                    "source": rec["_source_ledger"],
                    "failure_timestamp_utc": ts_utc,
                    "recovery_timestamp_utc": None,
                    "duration_seconds": None,
                    "status": "open",
                    "failure_type": fault_type,
                    "drill": rec.get("drill", False),
                    "evidence": {
                        "fault_record": rec
                    }
                }
        else:
            # We have an open incident. Check if it resolves.
            resolved = False
            
            if open_incident["failure_type"] == "executor_fault":
                if rec["_source_ledger"] == "executor_fault_ledger" and (rec.get("success") is True or rec.get("fault") is False):
                    resolved = True
            elif open_incident["failure_type"] == "watchdog_restart":
                if rec["_source_ledger"] == "watchdog_ledger" and rec.get("success") is True:
                    resolved = True
                    
            if resolved:
                open_incident["recovery_timestamp_utc"] = ts_utc
                start_ts = parse_iso(open_incident["failure_timestamp_utc"])
                end_ts = parse_iso(ts_utc)
                open_incident["duration_seconds"] = (end_ts - start_ts).total_seconds()
                open_incident["status"] = "resolved"
                open_incident["evidence"]["recovery_record"] = rec
                
                # Clean up internal markers before saving
                if "_source_ledger" in open_incident["evidence"]["fault_record"]:
                    del open_incident["evidence"]["fault_record"]["_source_ledger"]
                if "_source_ledger" in open_incident["evidence"]["recovery_record"]:
                    del open_incident["evidence"]["recovery_record"]["_source_ledger"]
                    
                incidents.append(open_incident)
                open_incident = None

    os.makedirs(os.path.dirname(INCIDENT_LEDGER), exist_ok=True)
    with open(INCIDENT_LEDGER, "w", encoding="utf-8") as f:
        for inc in incidents:
            f.write(json.dumps(inc) + "\n")
            
    print(f"Incident ledger built with {len(incidents)} resolved incidents.")

if __name__ == "__main__":
    build_incident_ledger()
