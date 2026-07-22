import os
import sys
import json
import time
import hashlib
import argparse

ESCROW_DIR = r"D:\Infinite\Infinity\Strategy\Execution_Escrow"
RECEIPTS_FILE = os.path.join(ESCROW_DIR, "execution_receipts.jsonl")
VERIFICATIONS_FILE = os.path.join(ESCROW_DIR, "execution_verification.jsonl")

def load_receipt(receipt_id):
    if not os.path.exists(RECEIPTS_FILE):
        return None
    with open(RECEIPTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            receipt = json.loads(line)
            if receipt.get("receipt_id") == receipt_id:
                return receipt
    return None

def count_previous_verifications(receipt_id):
    if not os.path.exists(VERIFICATIONS_FILE):
        return 0
    count = 0
    with open(VERIFICATIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            rec = json.loads(line)
            if rec.get("receipt_id") == receipt_id:
                count += 1
    return count

def verify_receipt(receipt_id):
    receipt = load_receipt(receipt_id)
    if not receipt:
        print(f"ERROR: Receipt {receipt_id} not found.")
        sys.exit(1)
        
    if not receipt.get("execution_performed"):
        print(f"ERROR: Receipt {receipt_id} is receipt-only (execution_performed=false). Cannot be verified.")
        sys.exit(1)
        
    materialized_path = receipt.get("materialized_path")
    expected_hash = receipt.get("content_sha256")
    proposal_id = receipt.get("proposal_id")
    
    if not materialized_path or not expected_hash:
        print("ERROR: Receipt is missing required materialization fields.")
        sys.exit(1)
        
    file_exists = os.path.exists(materialized_path)
    bytes_read = 0
    actual_hash = None
    verified = False
    
    if file_exists:
        with open(materialized_path, "rb") as f:
            content = f.read()
            bytes_read = len(content)
            actual_hash = hashlib.sha256(content).hexdigest()
            
        if actual_hash == expected_hash:
            verified = True
            
    prev_count = count_previous_verifications(receipt_id)
    attempt = prev_count + 1
    
    record = {
        "proposal_id": proposal_id,
        "receipt_id": receipt_id,
        "materialized_path": materialized_path,
        "content_sha256_expected": expected_hash,
        "content_sha256_actual": actual_hash,
        "verified": verified,
        "verified_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verification_attempt": attempt,
        "previous_verifications_for_receipt": prev_count,
        "file_exists": file_exists,
        "bytes_read": bytes_read
    }
    
    os.makedirs(ESCROW_DIR, exist_ok=True)
    with open(VERIFICATIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
        
    if verified:
        print(f"SUCCESS: Receipt {receipt_id} cleanly verified (Attempt {attempt}).")
    else:
        print(f"FAILURE: Receipt {receipt_id} failed verification (Attempt {attempt}).")
        if not file_exists:
            print("  -> File does not exist.")
        else:
            print(f"  -> Hash mismatch. Expected: {expected_hash[:8]}, Actual: {actual_hash[:8]}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execution Verification Verifier")
    parser.add_argument("--verify", type=str, required=True, help="Receipt ID to verify")
    args = parser.parse_args()

    verify_receipt(args.verify)
