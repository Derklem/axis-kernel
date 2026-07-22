import os
import json
import time
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
QUEUE_FILE = os.path.join(ROOT, "Governance", "Witness_Admission_Queue.jsonl")
DIRECT_INQUIRY = os.path.join(ROOT, "Inquiry", "Direct_Inquiry.jsonl")
REPORTS_DIR = os.path.join(ROOT, "Governance", "Reports")
REGISTRY_FILE = os.path.join(ROOT, "Governance", "lane_registry.json")

def admit_queue():
    if not os.path.exists(QUEUE_FILE):
        print("No Witness Admission Queue found.")
        return

    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            registry = json.load(f)
            classifications = registry.get("classifications", {})
    except Exception as e:
        print(f"Failed to load registry: {e}")
        return

    records = []
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    except Exception as e:
        print(f"Failed to read queue: {e}")
        return

    if not records:
        print("Queue is empty.")
        return

    valid_records = []
    rejected_records = []

    for rec in records:
        c = rec.get("classification")
        lane = classifications.get(c)
        
        reasons = []
        if lane != "witnessed":
            reasons.append(f"Classification '{c}' is not witnessed (found {lane}).")
        if not rec.get("rationale"):
            reasons.append("Missing 'rationale'.")
        if not rec.get("source"):
            reasons.append("Missing 'source'.")
        if rec.get("operator_ack") is not True:
            reasons.append("'operator_ack' is not true.")
        if rec.get("epistemic_cost_ack") is not True:
            reasons.append("'epistemic_cost_ack' is not true.")

        if reasons:
            rejected_records.append({
                "record": rec,
                "reasons": reasons
            })
        else:
            admission_record_id = f"grant-{int(time.time() * 1000)}"
            
            # Full record for granted report
            granted_record = rec.copy()
            granted_record["admission_record_id"] = admission_record_id
            granted_record["admission_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Clean minimal record for Direct Inquiry
            clean_record = {
                "id": rec.get("id"),
                "content": rec.get("content"),
                "status": "PENDING",
                "classification": rec.get("classification"),
                "source": rec.get("source"),
                "rationale": rec.get("rationale"),
                "admission_utc": granted_record["admission_utc"],
                "admission_record_id": admission_record_id
            }
            
            valid_records.append({
                "clean": clean_record,
                "full": granted_record
            })

    # Write granted reports
    if valid_records:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        timestamp = int(time.time() * 1000)
        granted_report_file = os.path.join(REPORTS_DIR, f"witness_admission_granted_{timestamp}.json")
        with open(granted_report_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "granted_count": len(valid_records),
                "admissions": [v["full"] for v in valid_records]
            }, f, indent=4)
            
        # Write valid records to Direct Inquiry
        os.makedirs(os.path.dirname(DIRECT_INQUIRY), exist_ok=True)
        with open(DIRECT_INQUIRY, "a", encoding="utf-8") as f:
            for vr in valid_records:
                f.write(json.dumps(vr["clean"]) + "\n")
        print(f"Admitted {len(valid_records)} records to Direct_Inquiry. See {granted_report_file}")

    # Write rejections to Reports
    if rejected_records:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        timestamp = int(time.time() * 1000)
        report_file = os.path.join(REPORTS_DIR, f"witness_admission_reject_{timestamp}.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "rejected_count": len(rejected_records),
                "rejections": rejected_records
            }, f, indent=4)
        print(f"Rejected {len(rejected_records)} records. See {report_file}")

    # Clear Queue
    open(QUEUE_FILE, "w", encoding="utf-8").close()

if __name__ == "__main__":
    admit_queue()
