import os
import sys
import json
from datetime import datetime, timezone

MIND_DIR = r"D:\Mind"
EVAL_DIR = os.path.join(MIND_DIR, "Evaluations")
MANIFEST_DIR = os.path.join(MIND_DIR, "ExecutionManifests")
RESULT_DIR = os.path.join(MIND_DIR, "Laboratory", "sandbox_results")
BELIEF_DIR = os.path.join(MIND_DIR, "BeliefUpdates", "pending")

INCLUDE_FIXTURES = False

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_latest_eval() -> str:
    if not os.path.exists(EVAL_DIR):
        return ""
    evals = [f for f in os.listdir(EVAL_DIR) if f.startswith("EVAL_") and f.endswith(".json")]
    evals.sort(reverse=True)
    
    for e in evals:
        path = os.path.join(EVAL_DIR, e)
        data = load_json(path)
        if data.get("fixture") is True and not INCLUDE_FIXTURES:
            continue
        return path
    return ""

def main():
    os.makedirs(BELIEF_DIR, exist_ok=True)
    
    # Allow explicit override via sys.argv for testing
    if len(sys.argv) > 1:
        eval_path = sys.argv[1]
    else:
        eval_path = get_latest_eval()
        
    if not eval_path or not os.path.exists(eval_path):
        print("No valid evaluation found.")
        return
        
    evaluation = load_json(eval_path)
    eval_id = evaluation.get("id")
    print(f"Checking Evaluation: {eval_id}")
    
        pointer_path = os.path.join(MIND_DIR, "Laboratory", "config", "current_policy.json")
    policy_path = None
    if os.path.exists(pointer_path):
        with open(pointer_path, 'r') as f:
            pointer = __import__('json').load(f)
            policy_path = os.path.join(os.path.dirname(pointer_path), pointer["path"])
    threshold = 0.30
    if os.path.exists(policy_path):
        policy_data = load_json(policy_path)
        threshold = float(policy_data.get("belief_update_effect_threshold", 0.30))

    # Check 1: Interpretation
    if evaluation.get("interpretation") != "supports_hypothesis":
        print(f"Rejected: Interpretation is '{evaluation.get('interpretation')}', not 'supports_hypothesis'")
        return
        
    # Check 2: Effect Size
    effect_size = evaluation.get("effect_size", 0.0)
    if effect_size < threshold:
        print(f"Rejected: Effect size ({effect_size}) is less than policy threshold ({threshold})")
        return
        
    # Check 3: Execution Context
    result_id = evaluation.get("source_result")
    result_path = os.path.join(RESULT_DIR, f"{result_id}.json")
    if not os.path.exists(result_path):
        print(f"Rejected: Source result missing: {result_path}")
        return
    result_data = load_json(result_path)
    if result_data.get("execution_context") != "sandbox":
        print(f"Rejected: Execution context is '{result_data.get('execution_context')}', not 'sandbox'")
        return
        
    # Check 4: Manifest Completion
    manifest_id = evaluation.get("source_manifest")
    manifest_path = os.path.join(MANIFEST_DIR, f"{manifest_id}.json")
    if not os.path.exists(manifest_path):
        print(f"Rejected: Source manifest missing: {manifest_path}")
        return
    manifest_data = load_json(manifest_path)
    if manifest_data.get("execution_status") != "completed":
        print(f"Rejected: Manifest execution_status is '{manifest_data.get('execution_status')}', not 'completed'")
        return
        
    # All checks passed. Emit proposal.
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    update_id = f"BELIEF_UPDATE_{timestamp}"
    
    proposal = {
        "id": update_id,
        "status": "pending",
        "fixture_source": evaluation.get("fixture", False),
        "source_evaluation": eval_id,
        "source_hypothesis": evaluation.get("source_hypothesis", "unknown"),
        "proposed_update": {
            "confidence_delta": 0.05,
            "reason": f"Sandbox result supports hypothesis with effect_size >= {threshold} (actual: {effect_size:.2f})"
        },
        "mutation_allowed": False,
        "requires_human_or_governance_approval": True
    }
    
    proposal_path = os.path.join(BELIEF_DIR, f"{update_id}.json")
    save_json(proposal_path, proposal)
    
    print(f"Belief Update Proposal generated: {os.path.basename(proposal_path)}")

if __name__ == "__main__":
    main()
