import os
import sys
import json
import shutil
from datetime import datetime, timezone

MIND_DIR = r"D:\Mind"
PENDING_DIR = os.path.join(MIND_DIR, "BeliefUpdates", "pending")
APPROVED_DIR = os.path.join(MIND_DIR, "BeliefUpdates", "approved")
REJECTED_DIR = os.path.join(MIND_DIR, "BeliefUpdates", "rejected")
GOV_DIR = os.path.join(MIND_DIR, "GovernanceDecisions")
INCLUDE_FIXTURES = "--allow-fixture" in sys.argv

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_latest_proposal() -> str:
    if not os.path.exists(PENDING_DIR):
        return ""
    proposals = [f for f in os.listdir(PENDING_DIR) if f.startswith("BELIEF_UPDATE_") and f.endswith(".json")]
    proposals.sort(reverse=True)
    
    for p in proposals:
        path = os.path.join(PENDING_DIR, p)
        data = load_json(path)
        if data.get("fixture_source") is True and not INCLUDE_FIXTURES:
            continue
        return path
    return ""

def main():
    os.makedirs(APPROVED_DIR, exist_ok=True)
    os.makedirs(REJECTED_DIR, exist_ok=True)
    os.makedirs(GOV_DIR, exist_ok=True)
    
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    if len(args) > 0:
        proposal_path = args[0]
    else:
        proposal_path = get_latest_proposal()
        
    if not proposal_path or not os.path.exists(proposal_path):
        print("No valid pending belief update proposal found.")
        return
        
    proposal = load_json(proposal_path)
    proposal_id = proposal.get("id")
    print(f"Checking Proposal: {proposal_id}")
    
    is_fixture = proposal.get("fixture_source", False)
    
    # Check 1: Requires authorization
    if proposal.get("requires_human_or_governance_approval") is not True:
        print("Rejected: Proposal does not require human or governance approval.")
        # Move to rejected
        shutil.move(proposal_path, os.path.join(REJECTED_DIR, os.path.basename(proposal_path)))
        return
        
    # Check 2: Mutation must currently be false
    if proposal.get("mutation_allowed") is not False:
        print("Rejected: Proposal already claims mutation_allowed == True.")
        shutil.move(proposal_path, os.path.join(REJECTED_DIR, os.path.basename(proposal_path)))
        return
        
    # All checks passed. Emit Governance Decision and move proposal to approved.
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    gov_id = f"GOV_DECISION_{timestamp}"
    
    reason = "Proposal structurally valid."
    if is_fixture:
        reason = "Proposal structurally valid; fixture override enabled for test run."
        
    confidence_delta = proposal.get("proposed_update", {}).get("confidence_delta", 0.0)
    
    decision = {
        "id": gov_id,
        "source_belief_update": proposal_id,
        "decision": "approved",
        "reason": reason,
        "mutation_authorized": True,
        "approved_confidence_delta": confidence_delta,
        "approval_scope": "single_hypothesis_confidence_update"
    }
    
    decision_path = os.path.join(GOV_DIR, f"{gov_id}.json")
    save_json(decision_path, decision)
    
    # Move the proposal file to approved
    shutil.move(proposal_path, os.path.join(APPROVED_DIR, os.path.basename(proposal_path)))
    
    print(f"Governance Decision generated: {os.path.basename(decision_path)}")
    print("Proposal moved to BeliefUpdates/approved.")

if __name__ == "__main__":
    main()
