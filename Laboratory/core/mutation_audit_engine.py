import os
import sys
import json
import hashlib
from datetime import datetime, timezone

MIND_DIR = r"D:\Mind"
RECEIPT_DIR = os.path.join(MIND_DIR, "MutationReceipts")
GOV_DIR = os.path.join(MIND_DIR, "GovernanceDecisions")
APPROVED_DIR = os.path.join(MIND_DIR, "BeliefUpdates", "approved")
ACTIVE_HYP_DIR = os.path.join(MIND_DIR, "Hypotheses", "active")
BACKUP_HYP_DIR = os.path.join(MIND_DIR, "Hypotheses", "backup")
AUDIT_DIR = os.path.join(MIND_DIR, "MutationAudits")

ALLOWED_CHANGED_FIELDS = ["confidence", "belief_update_history"]

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def hash_file(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Cannot hash missing file: {path}")
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def get_latest_receipt() -> str:
    if not os.path.exists(RECEIPT_DIR):
        return ""
    receipts = [f for f in os.listdir(RECEIPT_DIR) if f.startswith("MUTATION_RECEIPT_") and f.endswith(".json")]
    receipts.sort(reverse=True)
    if receipts:
        return os.path.join(RECEIPT_DIR, receipts[0])
    return ""

def find_unauthorized_changes(old_obj, new_obj, allowed_fields, prefix=""):
    unauthorized = []
    
    if isinstance(old_obj, dict) and isinstance(new_obj, dict):
        for k in set(old_obj.keys()).union(new_obj.keys()):
            path = f"{prefix}.{k}" if prefix else k
            
            if path in allowed_fields:
                continue
                
            if k not in old_obj:
                unauthorized.append(f"Added: {path}")
            elif k not in new_obj:
                unauthorized.append(f"Removed: {path}")
            else:
                unauthorized.extend(find_unauthorized_changes(old_obj[k], new_obj[k], allowed_fields, path))
    elif isinstance(old_obj, list) and isinstance(new_obj, list):
        if len(old_obj) != len(new_obj):
            unauthorized.append(f"List length changed at {prefix}")
        else:
            for i, (o, n) in enumerate(zip(old_obj, new_obj)):
                unauthorized.extend(find_unauthorized_changes(o, n, allowed_fields, f"{prefix}[{i}]"))
    else:
        if old_obj != new_obj:
            unauthorized.append(f"Changed: {prefix}")
            
    return unauthorized

def emit_failure(receipt_id: str, failure_stage: str, failure_reason: str):
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    audit_id = f"MUTATION_AUDIT_{timestamp}"
    audit_artifact = {
        "id": audit_id,
        "status": "failed",
        "source_receipt": receipt_id,
        "failure_stage": failure_stage,
        "failure_reason": failure_reason,
        "audit_result": "mutation_not_trusted"
    }
    audit_path = os.path.join(AUDIT_DIR, f"{audit_id}.json")
    save_json(audit_path, audit_artifact)
    print(f"Audit FAILED: {failure_stage} - {failure_reason}")
    print(f"Failure Artifact generated: {audit_id}")
    return

def main():
    os.makedirs(AUDIT_DIR, exist_ok=True)
    
    if len(sys.argv) > 1:
        receipt_path = sys.argv[1]
    else:
        receipt_path = get_latest_receipt()
        
    if not receipt_path or not os.path.exists(receipt_path):
        print("No valid mutation receipt found.")
        return
        
    receipt = load_json(receipt_path)
    receipt_id = receipt.get("id")
    print(f"Auditing Receipt: {receipt_id}")
    
    # 1. Load GOV_DECISION
    gov_id = receipt.get("gov_decision")
    gov_path = os.path.join(GOV_DIR, f"{gov_id}.json")
    if not os.path.exists(gov_path):
        return emit_failure(receipt_id, "missing_governance", f"Missing governance decision {gov_id}")
    gov_decision = load_json(gov_path)
    authorized_delta = gov_decision.get("approved_confidence_delta", 0.0)
    
    # 2. Load BELIEF_UPDATE
    update_id = gov_decision.get("source_belief_update")
    update_path = os.path.join(APPROVED_DIR, f"{update_id}.json")
    if not os.path.exists(update_path):
        return emit_failure(receipt_id, "missing_governance", f"Missing source belief update {update_id}")
        
    # 3. Load Active Hypothesis
    target_hyp_id = receipt.get("target_hypothesis")
    active_hyp_path = os.path.join(ACTIVE_HYP_DIR, f"{target_hyp_id}.json")
    if not os.path.exists(active_hyp_path):
        return emit_failure(receipt_id, "missing_backup", f"Missing active hypothesis {target_hyp_id}")
        
    # 4. Verify after hash
    actual_after_hash = hash_file(active_hyp_path)
    expected_after_hash = receipt.get("hypothesis_hash_after")
    
    if actual_after_hash != expected_after_hash:
        return emit_failure(receipt_id, "after_hash_check", f"Active hypothesis hash ({actual_after_hash}) does not match receipt's after hash ({expected_after_hash})")
        
    # 5. Find and verify backup hash
    expected_before_hash = receipt.get("hypothesis_hash_before")
    matched_backup_path = None
    
    if os.path.exists(BACKUP_HYP_DIR):
        for f in os.listdir(BACKUP_HYP_DIR):
            if f.startswith(f"{target_hyp_id}_") and f.endswith(".json"):
                b_path = os.path.join(BACKUP_HYP_DIR, f)
                b_hash = hash_file(b_path)
                if b_hash == expected_before_hash:
                    matched_backup_path = b_path
                    break
                    
    if not matched_backup_path:
        return emit_failure(receipt_id, "missing_backup", f"No backup found matching before hash {expected_before_hash}")
        
    # 6. Deep Differential Verification
    backup_hyp = load_json(matched_backup_path)
    active_hyp = load_json(active_hyp_path)
    
    old_conf = backup_hyp.get("confidence", 0.0)
    new_conf = active_hyp.get("confidence", 0.0)
    observed_delta = round(new_conf - old_conf, 4)  # Prevent floating point drift noise
    
    unauthorized_changes = find_unauthorized_changes(backup_hyp, active_hyp, ALLOWED_CHANGED_FIELDS)
    
    if observed_delta != round(authorized_delta, 4):
        unauthorized_changes.append(f"Delta mismatch: observed {observed_delta}, authorized {authorized_delta}")
        
    if unauthorized_changes:
        # Check if only delta failed or unauthorized fields changed
        if len(unauthorized_changes) == 1 and unauthorized_changes[0].startswith("Delta mismatch"):
            return emit_failure(receipt_id, "delta_check", "; ".join(unauthorized_changes))
        else:
            return emit_failure(receipt_id, "unauthorized_diff", "; ".join(unauthorized_changes))
    
    # Passed
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    audit_id = f"MUTATION_AUDIT_{timestamp}"
    
    audit_artifact = {
        "id": audit_id,
        "status": "passed",
        "source_receipt": receipt_id,
        "matched_backup_path": matched_backup_path,
        "authorized_delta": authorized_delta,
        "observed_delta": observed_delta,
        "allowed_changed_fields": ALLOWED_CHANGED_FIELDS,
        "unauthorized_changes": [],
        "audit_result": "mutation_exactly_authorized"
    }
    
    audit_path = os.path.join(AUDIT_DIR, f"{audit_id}.json")
    save_json(audit_path, audit_artifact)
    
    print(f"Audit PASSED: mutation_exactly_authorized")
    print(f"Audit Artifact generated: {audit_id}")

if __name__ == "__main__":
    main()
