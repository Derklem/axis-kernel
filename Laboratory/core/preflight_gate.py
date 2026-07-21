import os
import json
import re
import shutil
import sys
from datetime import datetime, timezone

MIND_DIR = r"D:\Mind"
PENDING_DIR = os.path.join(MIND_DIR, "Predictions", "pending")
APPROVED_DIR = os.path.join(MIND_DIR, "Predictions", "approved")
REJECTED_DIR = os.path.join(MIND_DIR, "Predictions", "rejected")
REVISION_DIR = os.path.join(MIND_DIR, "Predictions", "needs_revision")

MAX_RUNS = 10

VALID_IVS = {
    "model_parameter": [
        "temperature",
        "top_p",
        "top_k",
        "repeat_penalty"
    ],
    "prompt_parameter": [
        "prompt_format",
        "input_trust_framing",
        "prompt_defense_level",
        "extraction_architecture",
        "system_prompt",
        "schema_definition",
        "few_shot_examples"
    ],
    "environment_parameter": [
        "model",
        "context_window"
    ],
    "legacy_parameter": [
        "delta_clamp_enabled",
        "score_update_formula",
        "validator_version",
        "verifier_version",
        "old_score/new_score relation enforcement"
    ]
}

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def check_actionability(iv: str) -> tuple[bool, str]:
    iv_lower = iv.lower().strip()
    found = False
    for category, params in VALID_IVS.items():
        if iv_lower in params:
            found = True
            break
    if not found:
        return False, f"Independent variable '{iv}' is not mapped to any known generator hook or parameter category."
    return True, ""

def check_measurability(dv: str) -> tuple[bool, str]:
    dv_lower = dv.lower()
    valid_metrics = ["failure rate", "validation", "delta invariant", "pass rate", "resistance", "accuracy", "compliance"]
    if not any(m in dv_lower for m in valid_metrics):
        return False, f"Dependent variable '{dv}' cannot be measured by the runner or verifier."
    return True, ""

def check_attention_budget(procedure: list) -> tuple[bool, str, int]:
    text = " ".join(procedure).lower()

    patterns = [
        r"(?:at least\s+)?(\d+)\s+(?:runs|experiments|trials|iterations)",
        r"(?:runs|experiments|trials|iterations)\s*[:=]?\s*(\d+)"
    ]

    requested = []
    for pattern in patterns:
        requested.extend(int(x) for x in re.findall(pattern, text))

    max_requested = max(requested) if requested else 1

    if max_requested > MAX_RUNS:
        return False, (
            f"Requested runs ({max_requested}) exceeds MAX_RUNS ({MAX_RUNS}). "
            f"Reduce runs to <= {MAX_RUNS} or justify elevated budget."
        ), max_requested

    return True, "", max_requested

def process_design(file_path: str) -> None:
    design = load_json(file_path)
    if "preflight_result" in design:
        print(f"Skipping {file_path}, already preflighted.")
        return

    iv = design.get("independent_variable", "")
    if isinstance(iv, dict):
        iv_name = iv.get("name", "")
        allowed_values = iv.get("allowed_values", [])
    else:
        iv_name = iv
        allowed_values = []
        
    dv = design.get("dependent_variable", "")
    procedure = design.get("experimental_procedure", [])
    constants = design.get("constants", {})

    checks = []
    
    # 1. Actionability
    iv_ok, iv_reason = check_actionability(iv_name)
    if iv_ok and allowed_values and iv_name == "prompt_format":
        for val in allowed_values:
            if val not in ["natural_language", "explicit_json_schema"]:
                iv_ok = False
                iv_reason = f"Value '{val}' is not a permitted prompt_format."
    elif iv_ok and allowed_values and iv_name == "input_trust_framing":
        for val in allowed_values:
            if val not in ["no_explicit_trust_boundary", "explicit_untrusted_data_boundary"]:
                iv_ok = False
                iv_reason = f"Value '{val}' is not a permitted input_trust_framing."
    elif iv_ok and allowed_values and iv_name == "prompt_defense_level":
        for val in allowed_values:
            if val not in ["schema_only", "schema_and_boundary", "schema_boundary_and_resistance_demonstration"]:
                iv_ok = False
                iv_reason = f"Value '{val}' is not a permitted prompt_defense_level."
    elif iv_ok and allowed_values and iv_name == "extraction_architecture":
        for val in allowed_values:
            if val not in ["single_stage_baseline", "multi_stage_decomposition"]:
                iv_ok = False
                iv_reason = f"Value '{val}' is not a permitted extraction_architecture."
    checks.append({"check": "actionability", "passed": iv_ok, "reason": iv_reason})

    # 2. Constants Check (Single Variable Isolation)
    constants_ok = True
    constants_reason = ""
    if iv_name in ["prompt_format", "input_trust_framing", "prompt_defense_level", "extraction_architecture"]:
        required_constants = ["model", "temperature", "fixture", "system_prompt", "evaluator"]
        missing = [c for c in required_constants if c not in constants]
        if missing:
            constants_ok = False
            constants_reason = f"Missing required constants for isolation: {missing}"
    checks.append({"check": "isolation", "passed": constants_ok, "reason": constants_reason})

    # 3. Measurability
    dv_ok, dv_reason = check_measurability(dv)
    checks.append({"check": "measurability", "passed": dv_ok, "reason": dv_reason})

    # 4. Attention Budget
    budget_ok, budget_reason, detected_runs = check_attention_budget(procedure)
    checks.append({"check": "attention_budget", "passed": budget_ok, "reason": budget_reason})

    status = "approved"
    rejection_reason = None
    revision_required = None

    if not iv_ok or not dv_ok or not constants_ok:
        status = "rejected"
        rejection_reason = " ".join(c["reason"] for c in checks if not c["passed"] and c["check"] != "attention_budget")
    elif not budget_ok:
        status = "needs_revision"
        revision_required = budget_reason

    design["preflight_result"] = {
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "checks": checks,
        "attention_cost": "high" if not budget_ok else "medium",
        "estimated_compute_minutes": 20 if not budget_ok else 5,
        "detected_requested_runs": detected_runs,
        "rejection_reason": rejection_reason,
        "revision_required": revision_required
    }
    
    design["status"] = status

    filename = os.path.basename(file_path)
    if status == "approved":
        target_dir = APPROVED_DIR
    elif status == "rejected":
        target_dir = REJECTED_DIR
    else:
        target_dir = REVISION_DIR

    target_path = os.path.join(target_dir, filename)
    save_json(target_path, design)
    
    # Delete original pending file
    os.remove(file_path)
    print(f"Preflight complete: {filename} -> {status}")

if __name__ == "__main__":
    if not os.path.exists(PENDING_DIR):
        print("No pending directory found.")
        sys.exit(0)

    for filename in os.listdir(PENDING_DIR):
        if filename.endswith(".json"):
            process_design(os.path.join(PENDING_DIR, filename))
