import os
import json
import time
from datetime import datetime, timezone
import subprocess

ESCROW_DIR = r"D:\Infinite\Infinity\Strategy\Execution_Escrow"
RECEIPTS_FILE = os.path.join(ESCROW_DIR, "execution_receipts.jsonl")
VERIFICATIONS_FILE = os.path.join(ESCROW_DIR, "execution_verification.jsonl")
ORACLE_SCRIPT = r"D:\Infinite\Infinity\Runtime\Decision\Governance_Oracle_Local_v1.py"
METRICS_FILE = r"D:\Infinite\Infinity\Runtime\Decision\Governance_Metrics.json"

def test_mock_production():
    ts = datetime.now(timezone.utc).isoformat()
    mock_receipt = {
        "receipt_id": "MOCK-PROD-RCPT-1",
        "proposal_id": "AGP-MOCK-1",
        "operation": "create_report",
        "target_path": r"D:\Infinite\Infinity\Reports\mock_report.md",
        "content_sha256": "fakehash123",
        "execution_performed": True,
        "released_utc": ts,
        "drill": False
    }
    
    mock_verification = {
        "receipt_id": "MOCK-PROD-RCPT-1",
        "verified": False,
        "file_exists": True,
        "verified_utc": ts,
        "drill": False
    }
    
    # 1. Inject
    print("Injecting non-drill mock execution and verification...")
    with open(RECEIPTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(mock_receipt) + "\n")
    with open(VERIFICATIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(mock_verification) + "\n")
        
    # 2. Run Oracle
    print("\nRunning Oracle...")
    subprocess.run(["python", ORACLE_SCRIPT])
    
    # 3. Read Metrics
    print("\nReading Oracle Metrics...")
    with open(METRICS_FILE, "r", encoding="utf-8") as f:
        metrics = json.load(f)
        
    print(f"Metrics: verifications: {metrics.get('execution_verifications_last_24h')}")
    print(f"Metrics: failures: {metrics.get('execution_verification_failures_last_24h')}")
    print(f"Metrics: last status: {metrics.get('last_execution_verification_status')}")
    
    if metrics.get("execution_verification_failures_last_24h") >= 1 and \
       metrics.get("last_execution_verification_status") == "failed_hash_mismatch":
        print("=> MOCK TEST PASSED.")
    else:
        print("=> MOCK TEST FAILED.")
        
    # 4. Clean up (Set drill: true on the mocks)
    print("\nCleaning up mock data...")
    def mark_drill(filepath, target_id):
        if not os.path.exists(filepath): return
        lines = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                rec = json.loads(line)
                if rec.get("receipt_id") == target_id:
                    rec["drill"] = True
                lines.append(json.dumps(rec))
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
            
    mark_drill(RECEIPTS_FILE, "MOCK-PROD-RCPT-1")
    mark_drill(VERIFICATIONS_FILE, "MOCK-PROD-RCPT-1")
    
    # 5. Rerun Oracle to restore clean state
    subprocess.run(["python", ORACLE_SCRIPT])
    print("Cleanup complete.")

if __name__ == "__main__":
    test_mock_production()
