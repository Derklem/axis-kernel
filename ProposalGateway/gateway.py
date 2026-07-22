import json
import hashlib
import jsonschema
import os
from .parser import parse_llm_output
from .repair import apply_safe_repairs, check_substantive_omissions
from .provenance import verify_provenance

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schemas")
PLANNER_SCHEMA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "Planner", "schemas"))

def get_schema_hash(schema_path: str) -> str:
    with open(schema_path, "r") as f:
        # parse and hash canonical json
        schema = json.load(f)
        return hashlib.sha256(json.dumps(schema, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()

def derive_receipt_id(raw_input_hash: str, source_context_hash: str, schema_hash: str, gateway_version: str, timestamp_utc: float) -> str:
    material = json.dumps(
        {
            "raw_input_hash": raw_input_hash,
            "source_context_hash": source_context_hash,
            "schema_hash": schema_hash,
            "gateway_version": gateway_version,
            "timestamp_utc": timestamp_utc,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"GWREC_{digest[:16].upper()}"

def serialize_sets(obj):
    if isinstance(obj, set):
        return sorted(list(obj))
    return obj

def evaluate_proposal(raw_text: str, source_context: dict, now_utc: float) -> dict:
    """
    Pure function to evaluate and repair an LLM proposal.
    Returns a result dict containing gateway_status, candidate, and receipt.
    """
    raw_input_hash = hashlib.sha256(raw_text.encode('utf-8')).hexdigest()
    source_context_hash = hashlib.sha256(
        json.dumps(source_context, default=serialize_sets, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    
    raw_schema_path = os.path.join(SCHEMA_DIR, "raw_proposal.schema.json")
    schema_hash = get_schema_hash(raw_schema_path)
    
    gateway_version = "proposal_gateway_v1"
    
    receipt = {
        "gateway_receipt_id": derive_receipt_id(raw_input_hash, source_context_hash, schema_hash, gateway_version, now_utc),
        "raw_input_hash": raw_input_hash,
        "normalized_input_hash": None,
        "source_refs": [],
        "repairs": [],
        "reason_codes": [],
        "unknown_fields": [],
        "gateway_version": gateway_version,
        "schema_hash": schema_hash,
        "timestamp_utc": now_utc
    }
    
    # 1. Strict Extraction
    try:
        raw_dict = parse_llm_output(raw_text)
    except ValueError as e:
        receipt["reason_codes"].append(f"EXTRACTION_FAILED:{str(e)}")
        return {"gateway_status": "REJECTED", "candidate": None, "receipt": receipt}
        
    normalized_input_hash = hashlib.sha256(json.dumps(raw_dict, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()
    receipt["normalized_input_hash"] = normalized_input_hash
    
    # 2. Raw Proposal Validation (catch hallucinated fields)
    with open(raw_schema_path, "r") as f:
        raw_schema = json.load(f)
        
    validator = jsonschema.Draft7Validator(raw_schema)
    errors = sorted(validator.iter_errors(raw_dict), key=lambda e: e.path)
    
    allowed = set(raw_schema.get("properties", {}))
    unknown_keys = sorted(set(raw_dict.keys()) - allowed)
    
    if unknown_keys:
        for k in unknown_keys:
            val_canon = json.dumps(raw_dict[k], sort_keys=True, separators=(',', ':'))
            receipt["unknown_fields"].append({
                "field_name": k,
                "value_hash": hashlib.sha256(val_canon.encode('utf-8')).hexdigest()
            })
            receipt["reason_codes"].append(f"UNKNOWN_FIELD:{k}")
        return {"gateway_status": "NEEDS_REVISION", "candidate": None, "receipt": receipt}
        
    if errors:
        for error in errors:
            receipt["reason_codes"].append(f"SCHEMA_ERROR:{error.message}")
        return {"gateway_status": "REJECTED", "candidate": None, "receipt": receipt}
        
    # 3. Safe Canonical Repair
    candidate, repairs = apply_safe_repairs(raw_dict)
    receipt["repairs"] = repairs
    
    # 4. Provenance Verification
    receipt["source_refs"] = candidate.get("source_refs", [])
    if not verify_provenance(candidate, source_context):
        receipt["reason_codes"].append("PROVENANCE_FAILED")
        return {"gateway_status": "REJECTED", "candidate": None, "receipt": receipt}
        
    # 5. Missing Field Verification
    missing = check_substantive_omissions(candidate)
    if missing:
        receipt["reason_codes"].extend(missing)
        return {"gateway_status": "NEEDS_REVISION", "candidate": None, "receipt": receipt}
        
    # 6. Final Planner candidate.schema.json validation
    planner_schema_path = os.path.join(PLANNER_SCHEMA_DIR, "candidate.schema.json")
    with open(planner_schema_path, "r") as f:
        planner_schema = json.load(f)
        
    planner_validator = jsonschema.Draft7Validator(planner_schema)
    planner_errors = sorted(planner_validator.iter_errors(candidate), key=lambda e: e.path)
    if planner_errors:
        for e in planner_errors:
            receipt["reason_codes"].append(f"PLANNER_SCHEMA_ERROR:{e.message}")
        return {"gateway_status": "NEEDS_REVISION", "candidate": None, "receipt": receipt}
        
    # Valid
    status = "ACCEPTED_WITH_SAFE_REPAIRS" if repairs else "ACCEPTED"
    return {"gateway_status": status, "candidate": candidate, "receipt": receipt}
