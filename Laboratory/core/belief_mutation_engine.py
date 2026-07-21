import os
import sys
import json
import shutil
import hashlib
from datetime import datetime, timezone

MIND_DIR = r"D:\Mind"
GOV_DIR = os.path.join(MIND_DIR, "GovernanceDecisions")
APPROVED_DIR = os.path.join(MIND_DIR, "BeliefUpdates", "approved")
ACTIVE_HYP_DIR = os.path.join(MIND_DIR, "Hypotheses", "active")
BACKUP_HYP_DIR = os.path.join(MIND_DIR, "Hypotheses", "backup")
RECEIPT_DIR = os.path.join(MIND_DIR, "MutationReceipts")

ALLOW_FIXTURE = "--allow-fixture" in sys.argv

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

def get_latest_decision() -> str:
    if not os.path.exists(GOV_DIR):
        return ""
    decisions = [f for f in os.listdir(GOV_DIR) if f.startswith("GOV_DECISION_") and f.endswith(".json")]
    decisions.sort(reverse=True)
    
    if decisions:
        return os.path.join(GOV_DIR, decisions[0])
    return ""

def main():
    os.makedirs(BACKUP_HYP_DIR, exist_ok=True)
    os.makedirs(RECEIPT_DIR, exist_ok=True)
    
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    if len(args) > 0:
        decision_path = args[0]
    else:
        decision_path = get_latest_decision()
        
    if not decision_path or not os.path.exists(decision_path):
        print("No valid governance decision found.")
        return
        
    decision = load_json(decision_path)
    decision_id = decision.get("id")
    print(f"Checking Governance Decision: {decision_id}")
    
    if "fixture" in decision.get("reason", "").lower() and not ALLOW_FIXTURE:
        print("Rejected: Decision involves a fixture, but --allow-fixture flag was not provided.")
        return
        
    if decision.get("mutation_authorized") is not True:
        print("Rejected: Mutation is not authorized in the governance decision.")
        return
        
    if decision.get("approval_scope") != "single_hypothesis_confidence_update":
        print(f"Rejected: Unrecognized approval_scope '{decision.get('approval_scope')}'.")
        return
        
    # Load Belief Update
    update_id = decision.get("source_belief_update")
    update_path = os.path.join(APPROVED_DIR, f"{update_id}.json")
    if not os.path.exists(update_path):
        raise FileNotFoundError(f"Source belief update {update_id} not found in approved directory.")
        
    belief_update = load_json(update_path)
    if decision["source_belief_update"] != belief_update.get("id"):
        raise ValueError("Governance decision does not match loaded belief update.")
        
    if belief_update.get("fixture_source") and not ALLOW_FIXTURE:
        print("Rejected: Source belief update is a fixture, but --allow-fixture flag was not provided.")
        return
        
    # Load Hypothesis
    hyp_id = belief_update.get("source_hypothesis")
    hyp_path = os.path.join(ACTIVE_HYP_DIR, f"{hyp_id}.json")
    if not os.path.exists(hyp_path):
        raise FileNotFoundError(f"Target hypothesis {hyp_id} not found in active directory.")
        
    hypothesis = load_json(hyp_path)
    if belief_update["source_hypothesis"] != hypothesis.get("id"):
        raise ValueError("Belief update does not match target hypothesis.")
        
    hash_before = hash_file(hyp_path)
    
    # Perform mutation
    delta = decision.get("approved_confidence_delta", 0.0)
    old_confidence = hypothesis.get("confidence", 0.0)
    new_confidence = min(max(old_confidence + delta, 0.0), 1.0)
    
    hypothesis["confidence"] = new_confidence
    
    if "belief_update_history" not in hypothesis:
        hypothesis["belief_update_history"] = []
        
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    hypothesis["belief_update_history"].append({
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "gov_decision": decision_id,
        "belief_update": update_id,
        "delta": delta,
        "new_confidence": new_confidence
    })
    
    # Backup old hypothesis
    backup_path = os.path.join(BACKUP_HYP_DIR, f"{hyp_id}_{timestamp}.json")
    shutil.copy2(hyp_path, backup_path)
    
    # Save mutated hypothesis
    save_json(hyp_path, hypothesis)
    hash_after = hash_file(hyp_path)
    
    # Generate receipt
    receipt_id = f"MUTATION_RECEIPT_{timestamp}"
    receipt = {
        "id": receipt_id,
        "status": "applied",
        "gov_decision": decision_id,
        "target_hypothesis": hyp_id,
        "delta_applied": delta,
        "old_confidence": old_confidence,
        "new_confidence": new_confidence,
        "hypothesis_hash_before": hash_before,
        "hypothesis_hash_after": hash_after
    }
    
    receipt_path = os.path.join(RECEIPT_DIR, f"{receipt_id}.json")
    save_json(receipt_path, receipt)
    
    print(f"Mutation successfully applied to {hyp_id}.")
    print(f"Receipt generated: {receipt_id}")

if __name__ == "__main__":
    main()
