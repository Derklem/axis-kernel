import os
import sys
import json
import time
import hashlib

# Ensure we can import ProposalGateway and Planner
sys.path.append(r"D:\infinite\Infinity")

from ProposalGateway.gateway import evaluate_proposal as gw_evaluate
from Planner.service import build_agenda

SHADOW_DIR = r"D:\infinite\Infinity\Strategy\State\ShadowMode"
SHADOW_INPUTS = os.path.join(SHADOW_DIR, "shadow_inputs.jsonl")
SHADOW_RESULTS = os.path.join(SHADOW_DIR, "shadow_results.jsonl")
SHADOW_ERRORS = os.path.join(SHADOW_DIR, "shadow_errors.jsonl")

def load_processed_ids():
    processed = set()
    for path in [SHADOW_RESULTS, SHADOW_ERRORS]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            item = json.loads(line)
                            if "shadow_event_id" in item:
                                processed.add(item["shadow_event_id"])
                        except: pass
    return processed

def write_jsonl(path, item):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(item) + "\n")
        f.flush()

def normalize_legacy_intent(legacy_decision_list):
    if not legacy_decision_list:
        return None
    for p in legacy_decision_list:
        eval_block = p.get("evaluation", {})
        if eval_block.get("solver_accepted"):
            return {
                "candidate_id": p.get("candidate_id") or p.get("intent_id") or p.get("proposal_id", "unknown"),
                "is_accepted": True
            }
    return None

def extract_planner_intent(agenda):
    tasks = agenda.get("tasks", [])
    if not tasks:
        return None
    task = tasks[0]
    return {
        "candidate_id": task.get("candidate_id"),
        "priority_score": task.get("priority_score"),
        "execution_mode": task.get("execution_mode")
    }

def compare_intents(legacy_intent, planner_intent, identity_bridge):
    if legacy_intent is None and planner_intent is None:
        return "exact_match", None, []
    if legacy_intent is None and planner_intent is not None:
        return "material_disagreement", "PLANNER_ACTION_LEGACY_IDLE", ["Planner scheduled a task but legacy remained idle"]
    if planner_intent is None and legacy_intent is not None:
        return "material_disagreement", "LEGACY_ACTION_PLANNER_IDLE", ["Legacy executed a task but Planner scheduled nothing"]
    
    reasons = []
    
    # Try mapping
    mapped_gw_id = next((b["gateway_candidate_id"] for b in identity_bridge if b["legacy_candidate_id"] == legacy_intent["candidate_id"]), None)
    
    if mapped_gw_id and planner_intent["candidate_id"] == mapped_gw_id:
        match_type = "exact_match"
    elif legacy_intent["candidate_id"] == planner_intent["candidate_id"]:
        match_type = "exact_match"
    else:
        match_type = "material_disagreement"
        reasons.append(f"Candidate mismatch: legacy={legacy_intent['candidate_id']} -> gw={mapped_gw_id} != planner={planner_intent['candidate_id']}")
        
    disagreement_class = "NONE" if match_type in ["exact_match", "compatible_match"] else "INTENT_MISMATCH"
    
    return match_type, disagreement_class, reasons

def process_envelope(env):
    evaluation_utc = env.get("captured_utc", time.time())
    
    # 1. Gateway Pass
    accepted_candidates = []
    gateway_reason_codes = []
    gateway_repairs = 0
    gateway_receipts = []
    identity_bridge = []
    
    gateway_status_counts = {
        "ACCEPTED": 0,
        "ACCEPTED_WITH_SAFE_REPAIRS": 0,
        "NEEDS_REVISION": 0,
        "REJECTED": 0
    }
    
    gw_start = time.time()
    
    raw_llm_text = env.get("raw_llm_text")
    if raw_llm_text is not None:
        parser_exercised = True
        texts_to_evaluate = [raw_llm_text]
        raw_ps = [{}] # Minimal placeholder since we can't map reliably without parsing
    else:
        parser_exercised = False
        raw_ps = env.get("canonical_proposal", [])
        texts_to_evaluate = [json.dumps(p) for p in raw_ps]
        
    for raw_text, raw_p in zip(texts_to_evaluate, raw_ps):
        gw_res = gw_evaluate(
            raw_text, 
            source_context=env.get("source_context", {}), 
            now_utc=evaluation_utc
        )
        
        status = gw_res.get("gateway_status", "REJECTED")
        if status in gateway_status_counts:
            gateway_status_counts[status] += 1
        else:
            gateway_status_counts[status] = 1
            
        candidate = gw_res.get("candidate")
        if status in ("ACCEPTED", "ACCEPTED_WITH_SAFE_REPAIRS") and candidate:
            accepted_candidates.append(candidate)
            legacy_id = raw_p.get("candidate_id") or raw_p.get("intent_id") or raw_p.get("proposal_id", "unknown")
            identity_bridge.append({
                "legacy_candidate_id": legacy_id,
                "gateway_candidate_id": candidate.get("candidate_id")
            })
        
        receipt = gw_res.get("receipt", {})
        receipt_id = receipt.get("gateway_receipt_id")
        if receipt_id:
            gateway_receipts.append(receipt_id)
            
        gateway_reason_codes.extend(receipt.get("reason_codes", []))
        if receipt.get("repairs"):
            gateway_repairs += len(receipt.get("repairs"))
            
    gw_latency_ms = (time.time() - gw_start) * 1000
    
    # Coverage accounting
    proposal_count = len(texts_to_evaluate)
    total_processed = sum(gateway_status_counts.values())
    if proposal_count != total_processed:
        raise ValueError(f"Coverage mismatch: {proposal_count} proposals != {total_processed} processed statuses")
        
    accepted_count = gateway_status_counts.get("ACCEPTED", 0) + gateway_status_counts.get("ACCEPTED_WITH_SAFE_REPAIRS", 0)
    if len(accepted_candidates) != accepted_count:
        raise ValueError(f"Accepted mismatch: {len(accepted_candidates)} candidates != {accepted_count} accepted statuses")
    
    gateway_batch_status = "REJECTED"
    if accepted_count == len(texts_to_evaluate) and len(texts_to_evaluate) > 0:
        gateway_batch_status = "ALL_ACCEPTED"
    elif accepted_candidates:
        gateway_batch_status = "PARTIAL_ACCEPTANCE"
    elif gateway_status_counts.get("NEEDS_REVISION", 0) + gateway_status_counts.get("REJECTED", 0) == len(texts_to_evaluate) and len(texts_to_evaluate) > 0:
        gateway_batch_status = "NO_ACCEPTED_CANDIDATES"
    else:
        gateway_batch_status = "GATEWAY_ERROR"

    # 2. Planner Pass
    planner_start = time.time()
    agenda = build_agenda(
        candidates=accepted_candidates,
        constraints=env.get("planner_constraints", {}),
        policy_id="agenda_v1_uncertainty_age_cost",
        now_utc=evaluation_utc,
        policy_dir_override=None
    )
    planner_latency_ms = (time.time() - planner_start) * 1000
    
    # Conservation check
    assert len(agenda.get("tasks", [])) <= len(accepted_candidates), "Planner manufactured unauthorized tasks"
    
    if agenda.get("tasks"):
        planner_status = "ACCEPTED"
    
    # 3. Equivalence Pass
    legacy_intent = normalize_legacy_intent(env.get("legacy_decision", []))
    planner_intent = extract_planner_intent(agenda)
    
    if not accepted_candidates:
        planner_status = "NO_ACCEPTED_CANDIDATES"
    elif not agenda.get("tasks"):
        planner_status = "AGENDA_EMPTY"
    else:
        planner_status = "AGENDA_BUILT"
        
    match_type, disagreement_class, reasons = compare_intents(legacy_intent, planner_intent, identity_bridge)
    
    top_candidate_id = agenda["tasks"][0]["candidate_id"] if agenda.get("tasks") else None
    
    deterministic_result = {
        "shadow_event_id": env["shadow_event_id"],
        "cycle_id": env["cycle_id"],
        "evaluation_status": "SHADOW_COMPLETED",
        "gateway_coverage": ["repair", "planner_validation", "provenance"] if not parser_exercised else ["parser", "repair", "planner_validation", "provenance"],
        "parser_exercised": parser_exercised,
        "gateway_batch_status": gateway_batch_status,
        "gateway_status_counts": gateway_status_counts,
        "gateway_receipt_ids": sorted(gateway_receipts),
        "gateway_reason_codes": sorted(set(gateway_reason_codes)),
        "gateway_repairs": gateway_repairs,
        "planner_status": planner_status,
        "planner_top_candidate_id": top_candidate_id,
        "planner_priority_score": agenda["tasks"][0]["priority_score"] if agenda.get("tasks") else None,
        "legacy_intent": legacy_intent,
        "planner_intent": planner_intent,
        "equivalence_class": match_type,
        "disagreement_class": disagreement_class,
        "disagreement_reasons": reasons,
        "proposal_count": len(texts_to_evaluate),
        "accepted_count": len(accepted_candidates),
        "strategy_trust_policy_id": env.get("policy_id"),
        "planner_policy_id": "agenda_v1_uncertainty_age_cost",
        "policy_hash": env.get("policy_hash"),
        "identity_bridge": sorted(
            identity_bridge,
            key=lambda item: (
                item["legacy_candidate_id"],
                item["gateway_candidate_id"],
            )
        ),
        "worker_version": "shadow_worker_v1",
        "planner_version": env.get("planner_version", "unknown"),
        "gateway_version": env.get("gateway_version", "unknown"),
        "comparison_policy_version": env.get("comparison_policy_version", "unknown"),
        "planner_schema_hash": env.get("planner_schema_hash", "unknown"),
        "gateway_schema_hash": env.get("gateway_schema_hash", "unknown")
    }
    
    deterministic_result_hash = hashlib.sha256(
        json.dumps(
            deterministic_result,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    
    result = dict(deterministic_result)
    result["deterministic_result_hash"] = deterministic_result_hash
    result["gateway_latency_ms"] = gw_latency_ms
    result["planner_latency_ms"] = planner_latency_ms
    result["total_latency_ms"] = gw_latency_ms + planner_latency_ms
    
    return result

def main():
    import traceback
    if not os.path.exists(SHADOW_INPUTS):
        print("No shadow inputs found.")
        return
        
    processed_ids = load_processed_ids()
    print(f"Loaded {len(processed_ids)} processed events.")
    
    with open(SHADOW_INPUTS, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try:
                env = json.loads(line)
            except Exception as e:
                print(f"Failed to parse envelope: {e}")
                continue
                
            event_id = env.get("shadow_event_id")
            if not event_id or event_id in processed_ids:
                continue
                
            try:
                result = process_envelope(env)
                write_jsonl(SHADOW_RESULTS, result)
                processed_ids.add(event_id)
                print(f"Processed {event_id} -> {result['equivalence_class']}")
            except Exception as e:
                import traceback
                trace = traceback.format_exc()
                error_item = {
                    "shadow_event_id": event_id,
                    "cycle_id": env.get("cycle_id"),
                    "evaluation_status": "SHADOW_ERROR",
                    "exception_type": type(e).__name__,
                    "exception_hash": hashlib.sha256(trace.encode('utf-8')).hexdigest()[:16],
                    "sanitized_message": str(e)[:500],
                    "worker_version": "shadow_worker_v1"
                }
                write_jsonl(SHADOW_ERRORS, error_item)
                processed_ids.add(event_id)
                print(f"Error on {event_id}: {e}")

if __name__ == "__main__":
    main()
