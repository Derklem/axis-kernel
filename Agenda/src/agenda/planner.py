import json
import os
import copy
from typing import Dict, Any, Tuple
import jsonschema
from jsonschema import validate
from referencing import Registry, Resource

# Use laboratory canonical_hash for deterministic roots
from laboratory.crypto import canonical_hash

SAFE_INTEGER_MAX = 9007199254740991

def checked_multiply(a: int, b: int) -> int:
    result = a * b
    if not -SAFE_INTEGER_MAX <= result <= SAFE_INTEGER_MAX:
        raise ValueError("AGENDA_SCORE_OVERFLOW")
    return result

def checked_add(a: int, b: int) -> int:
    result = a + b
    if not -SAFE_INTEGER_MAX <= result <= SAFE_INTEGER_MAX:
        raise ValueError("AGENDA_SCORE_OVERFLOW")
    return result

def checked_sub(a: int, b: int) -> int:
    result = a - b
    if not -SAFE_INTEGER_MAX <= result <= SAFE_INTEGER_MAX:
        raise ValueError("AGENDA_SCORE_OVERFLOW")
    return result

def load_schema(schema_name: str) -> Dict[str, Any]:
    schema_path = os.path.join(os.path.dirname(__file__), "schemas", schema_name)
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def calculate_score(candidate: Dict[str, Any], spec: Dict[str, Any]) -> int:
    gain = candidate.get("expected_information_gain", 0)
    compute = candidate.get("estimated_compute_cost", 0)
    attention = candidate.get("estimated_attention_cost", 0)
    
    gw = spec.get("gain_weight", 0)
    cw = spec.get("compute_cost_weight", 0)
    aw = spec.get("attention_cost_weight", 0)
    
    term1 = checked_multiply(gain, gw)
    term2 = checked_multiply(compute, cw)
    term3 = checked_multiply(attention, aw)
    
    res = checked_sub(term1, term2)
    res = checked_sub(res, term3)
    return res

def generate_agenda(planner_input: Dict[str, Any], planner_spec: Dict[str, Any]) -> Dict[str, Any]:
    input_schema = load_schema("planner_input.json")
    spec_schema = load_schema("planner_spec.json")
    hypothesis_schema = load_schema("hypothesis_candidate.json")
    
    registry = Registry().with_resources([
        ("urn:axis:agenda:planner_input:v1.0.0", Resource.from_contents(input_schema)),
        ("urn:axis:agenda:planner_spec:v1.0.0", Resource.from_contents(spec_schema)),
        ("hypothesis_candidate.json", Resource.from_contents(hypothesis_schema)),
        ("urn:axis:agenda:hypothesis_candidate:v1.0.0", Resource.from_contents(hypothesis_schema)),
    ])
    
    def emit(payload: dict) -> dict:
        root = canonical_hash(payload)
        payload["agenda_root"] = root
        agenda_schema = load_schema("agenda.json")
        validate(instance=payload, schema=agenda_schema)
        return payload

    def emit_failure(reason_codes=None):
        payload = {
            "agenda_schema_version": "1.0.0",
            "status": "FAILED_INPUT_VALIDATION"
        }
        try:
            payload["planner_input_root"] = canonical_hash(planner_input)
            payload["planner_spec_root"] = canonical_hash(planner_spec)
        except ValueError:
            payload["reason_codes"] = ["NON_CANONICAL_INPUT"]
            
        if reason_codes:
            existing = payload.get("reason_codes", [])
            payload["reason_codes"] = list(set(existing + reason_codes))
            
        return emit(payload)

    try:
        jsonschema.validate(instance=planner_input, schema=input_schema, registry=registry)
        jsonschema.validate(instance=planner_spec, schema=spec_schema, registry=registry)
    except jsonschema.exceptions.ValidationError:
        return emit_failure()
        
    seen_ids = set()
    for c in planner_input["candidates"]:
        cid = c.get("candidate_id")
        if cid in seen_ids:
            return emit_failure(["DUPLICATE_CANDIDATE_ID"])
        seen_ids.add(cid)
    
    # Calculate scores and sort candidates
    scored_candidates = []
    try:
        for c in planner_input["candidates"]:
            score = calculate_score(c, planner_spec)
            scored_candidates.append({
                "candidate": c,
                "score": score
            })
    except ValueError as e:
        if str(e) == "AGENDA_SCORE_OVERFLOW":
            # If calculation overflows, it's also a validation failure
            return emit_failure(["AGENDA_SCORE_OVERFLOW"])
        raise
    
    # Sort by score descending, then candidate_id ascending
    scored_candidates.sort(key=lambda x: (-x["score"], x["candidate"]["candidate_id"]))
    
    ranked_items = []
    deferred_items = []
    rejected_items = []
    
    max_items = planner_spec["max_agenda_items"]
    max_compute = planner_spec["max_compute_budget"]
    max_attention = planner_spec["max_attention_budget"]
    
    current_compute = 0
    current_attention = 0
    
    for item in scored_candidates:
        c = item["candidate"]
        score = item["score"]
        compute_cost = c["estimated_compute_cost"]
        attention_cost = c["estimated_attention_cost"]
        cid = c["candidate_id"]
        
        # Check absolute constraints
        if compute_cost > max_compute:
            rejected_items.append({"candidate_id": cid, "score": score, "reason_code": "EXCEEDS_MAX_COMPUTE_BUDGET"})
            continue
        if attention_cost > max_attention:
            rejected_items.append({"candidate_id": cid, "score": score, "reason_code": "EXCEEDS_MAX_ATTENTION_BUDGET"})
            continue
            
        # Check cumulative constraints
        if len(ranked_items) >= max_items:
            deferred_items.append({"candidate_id": cid, "score": score, "reason_code": "AGENDA_FULL"})
            continue
            
        if current_compute + compute_cost > max_compute:
            deferred_items.append({"candidate_id": cid, "score": score, "reason_code": "INSUFFICIENT_COMPUTE_BUDGET"})
            continue
            
        if current_attention + attention_cost > max_attention:
            deferred_items.append({"candidate_id": cid, "score": score, "reason_code": "INSUFFICIENT_ATTENTION_BUDGET"})
            continue
            
        # Admitted
        ranked_items.append({"candidate_id": cid, "score": score})
        current_compute = checked_add(current_compute, compute_cost)
        current_attention = checked_add(current_attention, attention_cost)

    agenda = {
        "agenda_schema_version": "1.0.0",
        "planner_input_root": canonical_hash(planner_input),
        "planner_spec_root": canonical_hash(planner_spec),
        "status": "SUCCESS",
        "ranked_items": ranked_items,
        "deferred_items": deferred_items,
        "rejected_items": rejected_items,
        "summary": {
            "total_compute_cost": current_compute,
            "total_attention_cost": current_attention
        }
    }
    
    return emit(agenda)
