import os
import json
import time
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
REGISTRY_FILE = os.path.join(ROOT, "Governance", "lane_registry.json")
CONVERSATIONAL_INBOX = os.path.join(ROOT, "Communication", "Conversational_Inbox.jsonl")
WITNESSED_INBOX = os.path.join(ROOT, "Inquiry", "Direct_Inquiry.jsonl")
REJECTS_DIR = os.path.join(ROOT, "Communication", "FROM_AXS")
ARCHIVE_DIR = os.path.join(ROOT, "Communication", "ARCHIVE", "TO_AXS_PROCESSED")
BRIDGE_SCRIPT = r"D:\Infinite\Telescope\to_axs_bridge.py"
REPORTS_DIR = os.path.join(ROOT, "Governance", "Reports")

def read_jsonl(path):
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records

def read_json_files(directory, prefix=""):
    if not os.path.exists(directory):
        return []
    records = []
    for f in os.listdir(directory):
        if f.endswith(".json") and f.startswith(prefix):
            try:
                with open(os.path.join(directory, f), "r", encoding="utf-8-sig") as fh:
                    records.append(json.load(fh))
            except Exception:
                pass
    return records

def audit():
    report = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metrics": {
            "total_processed": 0,
            "total_accepted": 0,
            "total_rejected": 0
        },
        "routing_integrity": {
            "conversational_in_witnessed": False,
            "witnessed_in_conversational": False,
            "bypassed_router": False,
            "bridge_imports_router": False,
            "historical_bypass_count": 0,
            "current_bypass_count": 0
        },
        "rejections": {
            "missing_classification": 0,
            "unknown_classification": 0,
            "invalid_json_or_schema": 0
        },
        "lanes": {
            "conversational": 0,
            "witnessed": 0
        }
    }

    # Check Bridge Source
    try:
        with open(BRIDGE_SCRIPT, "r", encoding="utf-8") as f:
            content = f.read()
            if "from Governance.lane_router import route_payload" in content:
                report["routing_integrity"]["bridge_imports_router"] = True
    except Exception:
        pass

    # Read Rejects
    rejects = read_json_files(REJECTS_DIR, prefix="reject_")
    report["metrics"]["total_rejected"] = len(rejects)
    
    for r in rejects:
        reason = r.get("reason", "")
        if "Missing classification" in reason:
            report["rejections"]["missing_classification"] += 1
        elif "Unknown classification" in reason:
            report["rejections"]["unknown_classification"] += 1
        else:
            report["rejections"]["invalid_json_or_schema"] += 1

    # Read Inboxes
    conv_records = read_jsonl(CONVERSATIONAL_INBOX)
    wit_records = read_jsonl(WITNESSED_INBOX)
    
    report["metrics"]["total_accepted"] = len(conv_records) + len(wit_records)
    report["lanes"]["conversational"] = len(conv_records)
    report["lanes"]["witnessed"] = len(wit_records)

    # Integrity Checks
    # 1. Did conversational inputs avoid Direct_Inquiry?
    # We look for inputs in witnessed lane that have a conversational classification.
    # We need the registry to know what is what.
    registry = {"classifications": {}}
    if os.path.exists(REGISTRY_FILE):
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            registry = json.load(f)
            
    classifications = registry.get("classifications", {})

    ROUTER_EPOCH = "2026-06-03T01:05:00Z"

    for rec in wit_records:
        c = rec.get("classification")
        if not c:
            rec_time = rec.get("bridged_utc") or rec.get("received_utc") or "1970"
            if rec_time < ROUTER_EPOCH:
                report["routing_integrity"]["historical_bypass_count"] += 1
            else:
                report["routing_integrity"]["current_bypass_count"] += 1
                report["routing_integrity"]["bypassed_router"] = True
        elif classifications.get(c) == "conversational":
            report["routing_integrity"]["conversational_in_witnessed"] = True
            
    for rec in conv_records:
        c = rec.get("classification")
        if not c:
            rec_time = rec.get("bridged_utc") or rec.get("received_utc") or "1970"
            if rec_time < ROUTER_EPOCH:
                report["routing_integrity"]["historical_bypass_count"] += 1
            else:
                report["routing_integrity"]["current_bypass_count"] += 1
                report["routing_integrity"]["bypassed_router"] = True
        elif classifications.get(c) == "witnessed":
            report["routing_integrity"]["witnessed_in_conversational"] = True

    # Total Processed
    report["metrics"]["total_processed"] = report["metrics"]["total_accepted"] + report["metrics"]["total_rejected"]

    # Write Report
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_file = os.path.join(REPORTS_DIR, f"governance_audit_{int(time.time() * 1000)}.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
        
    print(f"Governance Audit complete. Report written to {report_file}")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    audit()
