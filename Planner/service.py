from Planner.intake import load_policy, get_policy_hash, get_schema_hash, hash_dict
from Planner.normalization import normalize_candidate
from Planner.validator import validate_candidate
from Planner.eligibility import check_eligibility
from Planner.scoring import score_candidate
from Planner.receipts import build_decision_receipt
from Planner.agenda_builder import build_agenda_snapshot

def build_agenda(candidates: list, constraints: dict, policy_id: str, now_utc: float, policy_dir_override: str = None) -> dict:
    """
    Main entry point for Planner v1 pipeline.
    """
    policy = load_policy(policy_id, policy_dir_override)
    policy_hash = get_policy_hash(policy_id, policy_dir_override)
    schema_hash = get_schema_hash(policy_id, policy_dir_override)
    
    receipts = []
    scored_tasks = []
    
    existing_candidate_ids = set()

    for raw_candidate in candidates:
        # 1. Normalization
        candidate = normalize_candidate(raw_candidate)
        
        # 2. Structural Validation
        validation_errors = validate_candidate(candidate)
        if validation_errors:
            receipt = build_decision_receipt(
                candidate,
                status="NEEDS_REVISION",
                reasons=validation_errors,
                policy_hash=policy_hash,
                timestamp_utc=now_utc
            )
            receipts.append(receipt)
            continue
            
        # 3. Eligibility Gates
        eligibility_reasons = check_eligibility(candidate, constraints, existing_candidate_ids)
        if eligibility_reasons:
            status = "DUPLICATE" if "DUPLICATE_CANDIDATE" in eligibility_reasons else "BLOCKED"
            receipt = build_decision_receipt(
                candidate,
                status=status,
                reasons=eligibility_reasons,
                policy_hash=policy_hash,
                timestamp_utc=now_utc
            )
            receipts.append(receipt)
            continue
            
        # 4. Deterministic Scoring
        existing_candidate_ids.add(candidate["candidate_id"])
        
        scored_result = score_candidate(candidate, policy)
        
        # Keep candidate dict, add score info
        task = dict(candidate)
        task["priority_score"] = scored_result["priority_score"]
        task["score_breakdown"] = scored_result["score_breakdown"]
        task["candidate_hash"] = hash_dict(candidate)
        
        scored_tasks.append(task)
        
        # Eligible Receipt
        receipt = build_decision_receipt(
            candidate,
            status="ELIGIBLE",
            reasons=[],
            policy_hash=policy_hash,
            timestamp_utc=now_utc
        )
        receipts.append(receipt)
        
    # 5. Assemble final agenda
    agenda = build_agenda_snapshot(scored_tasks, receipts, policy_hash, schema_hash, now_utc)
    
    return agenda
