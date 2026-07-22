import hashlib
import json

def build_agenda_snapshot(scored_tasks: list, receipts: list, policy_hash: str, schema_hash: str, timestamp_utc: float) -> dict:
    """
    Assembles the final Agenda object, sorting tasks by priority_score descending.
    """
    sorted_tasks = sorted(
        scored_tasks, 
        key=lambda task: (
            -task.get("priority_score", 0),
            task.get("candidate_id", ""),
            task.get("candidate_hash", "")
        )
    )
    
    # Map scored_tasks to the schema format
    formatted_tasks = []
    for t in sorted_tasks:
        formatted_tasks.append({
            "candidate_id": t["candidate_id"],
            "priority_score": t["priority_score"],
            "score_breakdown": t["score_breakdown"],
            "execution_mode": t.get("execution_mode", "human_approval")
        })

    # Sort receipts so hashes are deterministic
    # We sort by the canonical JSON hash of the receipt to establish a total order
    def hash_receipt(r):
        return hashlib.sha256(json.dumps(r, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
        
    sorted_receipts = sorted(receipts, key=hash_receipt)
    receipt_hashes = [hash_receipt(r) for r in sorted_receipts]
    
    receipts_root_hash = hashlib.sha256(
        json.dumps(receipt_hashes, separators=(',', ':')).encode('utf-8')
    ).hexdigest()

    agenda = {
        "policy_hash": policy_hash,
        "schema_hash": schema_hash,
        "builder_version": "planner_v1",
        "timestamp_utc": timestamp_utc,
        "planner_intent": {
            "candidate_id": formatted_tasks[0]["candidate_id"],
            "priority_score": formatted_tasks[0]["priority_score"],
            "execution_mode": formatted_tasks[0]["execution_mode"]
        } if formatted_tasks else None,
        "tasks": formatted_tasks,
        "receipt_hashes": receipt_hashes,
        "receipts_root_hash": receipts_root_hash,
        "receipts": sorted_receipts
    }
    
    return agenda
