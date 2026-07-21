import os
import json
import re
import sys
from datetime import datetime, timezone

from gemma_bridge import query_gemma

MIND_DIR = r"D:\Mind"
LAB_DIR = os.path.join(MIND_DIR, "Laboratory")

HYP_ACTIVE_DIR = os.path.join(MIND_DIR, "Hypotheses", "active")
BUNDLES_DIR = os.path.join(LAB_DIR, "research_bundles")
PENDING_DIR = os.path.join(MIND_DIR, "Predictions", "pending")


def utc_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def latest_json_file(directory: str, prefix: str) -> str:
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Missing directory: {directory}")

    candidates = [
        os.path.join(directory, name)
        for name in os.listdir(directory)
        if name.startswith(prefix) and name.endswith(".json")
    ]

    if not candidates:
        raise FileNotFoundError(f"No {prefix}*.json files found in {directory}")

    return max(candidates, key=os.path.getmtime)


def clean_json_response(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text, flags=re.MULTILINE).strip()
    text = re.sub(r"```$", "", text, flags=re.MULTILINE).strip()
    return text


def build_design_prompt(hypothesis: dict, bundle: dict) -> str:
    return f"""
You are the Experimental Design Engine of an AI Laboratory.

Your task:
Convert the active hypothesis into a concrete experimental design.

SCIENTIFIC QUALITY GATES (CRITICAL):
1. `independent_variable` MUST name exactly ONE manipulable variable (e.g., "delta_clamp_enabled", "score_update_formula", "validator_version"). DO NOT use vague plurals like "parameters", "logic", or "function behavior".
2. `prediction_interval` MUST be epistemically honest. Do not use overconfident, narrow intervals like [0.95, 1.0] without prior calibration. Represent genuine uncertainty (e.g., [0.55, 0.85]).
3. `expected_success_probability` MUST be an independent estimate of the experiment's success, NOT a direct copy of the hypothesis confidence.
4. `falsification_condition` MUST describe DISCONFIRMING evidence. If your condition says "If the modified logic passes the tests...", that SUPPORTS the hypothesis. True falsification is logically inverted: e.g., "If the original logic passes unchanged, or if failures persist after applying a known invariant-preserving fix, the hypothesis is falsified."

You must define:
- independent variable
- dependent variable
- controlled variables
- predicted effect
- prediction interval
- expected success probability
- experimental procedure
- measurement plan
- falsification condition

Do not execute the experiment.
Do not invent evidence.
Do not cite experiment IDs not present in the source hypothesis or evidence bundle.

SOURCE HYPOTHESIS:
{json.dumps(hypothesis, indent=2)}

EVIDENCE BUNDLE SUMMARY:
bundle_id: {bundle.get("bundle_id")}
evidence_hash: {bundle.get("evidence_hash")}
available_experiments: {list(bundle.get("evidence", {}).keys())}

OUTPUT JSON ONLY.
No markdown.
No commentary.

Required JSON schema:
{{
  "independent_variable": "...",
  "dependent_variable": "...",
  "controlled_variables": ["..."],
  "predicted_effect": "...",
  "prediction_interval": [0.0, 1.0],
  "expected_success_probability": 0.0,
  "experimental_procedure": ["..."],
  "measurement_plan": ["..."],
  "falsification_condition": "..."
}}
""".strip()


def validate_design(raw: dict, hypothesis_confidence: float) -> None:
    # 1. Base Schema Validation
    required = [
        "independent_variable",
        "dependent_variable",
        "controlled_variables",
        "predicted_effect",
        "prediction_interval",
        "expected_success_probability",
        "experimental_procedure",
        "measurement_plan",
        "falsification_condition",
    ]

    for key in required:
        if key not in raw:
            raise ValueError(f"Missing required key: {key}")

    iv = str(raw["independent_variable"]).strip()
    if not iv:
        raise ValueError("independent_variable is empty")

    if not str(raw["dependent_variable"]).strip():
        raise ValueError("dependent_variable is empty")

    if not isinstance(raw["controlled_variables"], list) or not raw["controlled_variables"]:
        raise ValueError("controlled_variables must be a non-empty list")

    interval = raw["prediction_interval"]
    if (
        not isinstance(interval, list)
        or len(interval) != 2
        or not all(isinstance(x, (int, float)) for x in interval)
        or interval[0] > interval[1]
    ):
        raise ValueError("prediction_interval must be [low, high]")

    prob = raw["expected_success_probability"]
    if not isinstance(prob, (int, float)) or prob < 0 or prob > 1:
        raise ValueError("expected_success_probability must be between 0 and 1")

    if not isinstance(raw["experimental_procedure"], list) or not raw["experimental_procedure"]:
        raise ValueError("experimental_procedure must be a non-empty list")

    if not isinstance(raw["measurement_plan"], list) or not raw["measurement_plan"]:
        raise ValueError("measurement_plan must be a non-empty list")
        
    fc = str(raw["falsification_condition"]).strip()
    if not fc:
        raise ValueError("falsification_condition is empty")

    # 2. Scientific Quality Gate Validation
    
    # Check IV for vague/plural terms
    vague_terms = ["parameters", "logic", "function behavior", "variables", "factors"]
    iv_lower = iv.lower()
    for term in vague_terms:
        if term in iv_lower:
            raise ValueError(f"Scientific Quality Gate Failed: independent_variable contains vague/plural term '{term}'. Must name exactly ONE manipulable variable.")
            
    # Check prediction interval width
    interval_width = interval[1] - interval[0]
    if interval_width < 0.1:
        raise ValueError(f"Scientific Quality Gate Failed: prediction_interval width ({interval_width:.2f}) is too narrow without prior calibration. Use an epistemically honest range.")
        
    # Check if prob is direct copy of confidence
    if abs(prob - hypothesis_confidence) < 0.001:
        raise ValueError("Scientific Quality Gate Failed: expected_success_probability is copied directly from hypothesis confidence. It must be an independent estimate.")
        
    # Check falsification logic (heuristic)
    fc_lower = fc.lower()
    
    if (
        "delta_clamp_enabled is true" in fc_lower
        and "delta_clamp_enabled is false" in fc_lower
        and "fails" in fc_lower
        and "proven false" in fc_lower
    ):
        raise ValueError(
            "Scientific Quality Gate Failed: falsification condition appears inverted. "
            "Passing with clamp enabled and failing without clamp supports the hypothesis."
        )

    bad_phrases = ["supports the hypothesis", "proves it true", "passes all validation tests"]
    for phrase in bad_phrases:
        if phrase in fc_lower:
            raise ValueError(
                f"Scientific Quality Gate Failed: falsification_condition contains suspicious phrase '{phrase}'."
            )


def main() -> None:
    os.makedirs(PENDING_DIR, exist_ok=True)

    hyp_path = latest_json_file(HYP_ACTIVE_DIR, "HYP_")
    hypothesis = load_json(hyp_path)

    bundle_id = hypothesis.get("evidence_bundle_id")
    evidence_hash = hypothesis.get("evidence_hash")
    hypothesis_confidence = float(hypothesis.get("confidence", 0.0))

    if not bundle_id:
        raise ValueError("Hypothesis missing evidence_bundle_id")

    bundle_path = os.path.join(BUNDLES_DIR, f"{bundle_id}.json")
    if not os.path.exists(bundle_path):
        raise FileNotFoundError(f"Referenced evidence bundle not found: {bundle_path}")

    bundle = load_json(bundle_path)

    if bundle.get("evidence_hash") != evidence_hash:
        raise ValueError("Evidence hash mismatch between hypothesis and bundle")

    prompt = build_design_prompt(hypothesis, bundle)

    print(f"Designing experiment from hypothesis: {hypothesis.get('id')}")
    response = query_gemma(prompt, temperature=0.0)
    cleaned = clean_json_response(response)

    try:
        raw_design = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print("Gemma returned invalid JSON.")
        print(cleaned)
        raise e

    validate_design(raw_design, hypothesis_confidence)

    design_id = utc_id("EXP_DESIGN")

    final_design = {
        "id": design_id,
        "status": "pending",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_hypothesis_id": hypothesis.get("id"),
        "evidence_bundle_id": bundle_id,
        "evidence_hash": evidence_hash,
        "independent_variable": raw_design["independent_variable"],
        "dependent_variable": raw_design["dependent_variable"],
        "controlled_variables": raw_design["controlled_variables"],
        "predicted_effect": raw_design["predicted_effect"],
        "prediction_interval": raw_design["prediction_interval"],
        "expected_success_probability": raw_design["expected_success_probability"],
        "experimental_procedure": raw_design["experimental_procedure"],
        "measurement_plan": raw_design["measurement_plan"],
        "falsification_condition": raw_design["falsification_condition"],
        "source_engine": "experimental_design_engine.py",
        "model_used": "gemma3:4b",
    }

    out_path = os.path.join(PENDING_DIR, f"{design_id}.json")
    save_json(out_path, final_design)

    print(f"Experimental design saved: {out_path}")


if __name__ == "__main__":
    main()
