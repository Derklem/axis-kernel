import os
import sys
import json
import datetime
import glob
from pathlib import Path

COMM_DIR = r"D:\Infinite\Infinity\Communication"
APPROVED_DIR = os.path.join(COMM_DIR, "approved")
ARCHIVED_DIR = os.path.join(COMM_DIR, "archived")
RECEIPTS_DIR = os.path.join(COMM_DIR, "receipts")
RECOVERY_DIR = os.path.join(COMM_DIR, "recovery")
LOCK_FILE = os.path.join(COMM_DIR, ".actuating")

def main():
    print("--- ACTUATING Lock Recovery Utility ---")
    
    if not os.path.exists(LOCK_FILE):
        print("No .actuating lock found. System is clean.")
        sys.exit(0)
        
    with open(LOCK_FILE, "r") as f:
        try:
            lock_data = json.load(f)
        except Exception as e:
            print(f"Failed to parse lock file: {e}")
            print("Preserving corrupted lock file for forensics...")
            timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            corrupt_copy = os.path.join(RECOVERY_DIR, f"CORRUPTED_ACTUATION_LOCK_{timestamp_str}.bin")
            # Close the file before moving
            f.close()
            os.replace(LOCK_FILE, corrupt_copy)
            
            # Write a recovery record for the corrupt lock
            record_fname = f"ACTUATION_LOCK_RECOVERED_CORRUPTED_{timestamp_str}.json"
            record_path = os.path.join(RECOVERY_DIR, record_fname)
            with open(record_path, "w", encoding="utf-8") as rf:
                json.dump({
                    "recovered_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "error": str(e),
                    "corrupted_lock_path": corrupt_copy
                }, rf, indent=2)
                
            print(f"Corrupted lock moved to: {corrupt_copy}")
            print(f"Recovery record written to: {record_path}")
            sys.exit(1)
            
    draft_id = lock_data.get("draft_id", "UNKNOWN")
    exp_id = lock_data.get("experiment_id", "UNKNOWN")
    
    print(f"Stale lock found for {exp_id} (Draft: {draft_id})")
    print(f"Started at: {lock_data.get('started_at')}")
    print(f"Process ID: {lock_data.get('process_id')}")
    
    # Check what state we are in
    draft_in_approved = any(f.endswith(".json") and draft_id in f for f in os.listdir(APPROVED_DIR))
    draft_in_archived = any(f.endswith(".json") and draft_id.replace('draft_', '') in f for f in os.listdir(ARCHIVED_DIR))
    
    print("\n[DIAGNOSTICS]")
    print(f"- Draft in approved/: {draft_in_approved}")
    print(f"- Draft in archived/: {draft_in_archived}")
    
    # Check for recovery artifacts
    recovery_files = glob.glob(os.path.join(RECOVERY_DIR, f"PENDING_DEPLOYMENT_RECONCILIATION_{exp_id}_*.json"))
    if recovery_files:
        print(f"- Found {len(recovery_files)} recovery artifacts in recovery/")
        for r in recovery_files:
            print(f"  > {r}")
    else:
        print("- No recovery artifacts found in recovery/")
        
    print("\nIf you are sure the process has crashed and you have resolved the ambiguity (e.g. by manual cleanup), you can remove the lock.")
    confirm = input("Type 'RECOVER' to clear the lock and write an audit record: ")
    
    if confirm == "RECOVER":
        timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        record_fname = f"ACTUATION_LOCK_RECOVERED_{exp_id}_{timestamp_str}.json"
        record_path = os.path.join(RECOVERY_DIR, record_fname)
        
        record = {
            "recovered_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "experiment_id": exp_id,
            "draft_id": draft_id,
            "lock_data_snapshot": lock_data,
            "diagnostics": {
                "draft_in_approved": draft_in_approved,
                "draft_in_archived": draft_in_archived,
                "recovery_files_found": len(recovery_files)
            },
            "operator_confirmation": True
        }
        
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
            
        os.remove(LOCK_FILE)
        print(f"\n[SUCCESS] Stale lock removed. Audit record written to: {record_path}")
    else:
        print("\n[ABORTED] Lock remains in place.")
        sys.exit(0)

if __name__ == "__main__":
    main()
