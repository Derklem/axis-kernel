import hashlib
import json

def generate_deterministic_id(candidate: dict) -> str:
    """Generates a PROP_ ID from canonical content of identity fields."""
    safe_copy = {
        "objective": candidate.get("objective"),
        "expected_information_gain": candidate.get("expected_information_gain"),
        "estimated_compute_minutes": candidate.get("estimated_compute_minutes"),
        "epistemic_debt_age_hours": candidate.get("epistemic_debt_age_hours"),
        "dependencies": candidate.get("dependencies", []),
        "source_refs": candidate.get("source_refs", [])
    }
    
    canonical_json = json.dumps(safe_copy, sort_keys=True, separators=(',', ':'))
    h = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()[:16].upper()
    return f"PROP_{h}"

def apply_safe_repairs(candidate: dict) -> tuple[dict, list[dict]]:
    """
    Applies safe canonical repairs in strict order. Returns repaired candidate and records.
    """
    repaired = dict(candidate)
    records = []
    
    # 1. Numeric string conversions
    for key in ["expected_information_gain", "epistemic_debt_age_hours", "estimated_compute_minutes"]:
        val = repaired.get(key)
        if isinstance(val, str):
            try:
                num_val = float(val) if '.' in val else int(val)
                repaired[key] = num_val
                records.append({
                    "repair_code": f"CONVERTED_NUMERIC_STRING_{key.upper()}",
                    "original_value": val,
                    "repaired_value": num_val
                })
            except ValueError:
                pass
                
    # 2. Canonical strings (whitespace trimming, enum casing)
    for key, val in repaired.items():
        if isinstance(val, str):
            trimmed = val.strip()
            if key == "risk_level":
                trimmed = trimmed.upper()
            if key in ("execution_mode", "status"):
                trimmed = trimmed.lower()
                
            if trimmed != val:
                repaired[key] = trimmed
                records.append({
                    "repair_code": f"NORMALIZED_STRING_{key.upper()}",
                    "original_value": val,
                    "repaired_value": trimmed
                })
                
    # 3. Sort arrays deterministically
    for key in ["source_refs", "dependencies", "constraints"]:
        if key in repaired and isinstance(repaired[key], list):
            sorted_arr = sorted(repaired[key])
            if sorted_arr != repaired[key]:
                repaired[key] = sorted_arr
                records.append({
                    "repair_code": f"SORTED_ARRAY_{key.upper()}",
                    "original_value": candidate[key],
                    "repaired_value": sorted_arr
                })

    # 4. Add default status
    if "status" not in repaired:
        repaired["status"] = "candidate"
        records.append({
            "repair_code": "ADDED_DEFAULT_STATUS",
            "original_value": None,
            "repaired_value": "candidate"
        })

    # 5. Identity generation LAST
    if not repaired.get("candidate_id"):
        new_id = generate_deterministic_id(repaired)
        repaired["candidate_id"] = new_id
        records.append({
            "repair_code": "GENERATED_CONTENT_DERIVED_CANDIDATE_ID",
            "original_value": None,
            "repaired_value": new_id
        })
                
    return repaired, records

def check_substantive_omissions(candidate: dict) -> list[str]:
    """Returns a list of missing substantive fields."""
    required = [
        "title",
        "objective",
        "expected_information_gain",
        "epistemic_debt_age_hours",
        "estimated_compute_minutes",
        "attention_cost",
        "risk_level",
        "execution_mode",
        "dependencies",
        "constraints",
        "source_refs"
    ]
    missing = []
    for r in required:
        if r not in candidate or candidate[r] is None or (isinstance(candidate[r], str) and candidate[r] == ""):
            missing.append(f"MISSING_FIELD:{r}")
    return missing
