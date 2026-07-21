import os
import json
import hashlib
import urllib.request
import urllib.error
import time
from datetime import datetime, timezone
import uuid

OLLAMA_API = "http://localhost:11434/api/generate"
MODEL = "llama3:latest"
TEMPERATURE = 0.0

SCHEMA_KEYS = {"incident_id", "event_type", "severity", "entities", "occurred_utc", "summary"}
SEVERITY_VALUES = {"LOW", "MEDIUM", "HIGH"}

SYSTEM_PROMPT = "You are a helpful assistant."

def sha256_hash(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def query_ollama(prompt: str) -> dict:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "temperature": TEMPERATURE,
        "stream": False,
        "options": {
            "num_predict": 500
        }
    }
    req = urllib.request.Request(OLLAMA_API, data=json.dumps(payload).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'})
    start = time.time()
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            latency = (time.time() - start) * 1000
            return result.get("response", ""), latency
    except Exception as e:
        latency = (time.time() - start) * 1000
        return str(e), latency

def validate_schema(raw: str):
    valid = False
    repaired = False
    errors = []
    parsed_json = None
    
    # 1. Parse check
    try:
        parsed_json = json.loads(raw)
    except json.JSONDecodeError as e:
        errors.append(f"JSON Parse Error: {e}")
        # Test repairability by stripping markdown code blocks
        clean_raw = raw.strip()
        if clean_raw.startswith("```json"):
            clean_raw = clean_raw[7:]
        elif clean_raw.startswith("```"):
            clean_raw = clean_raw[3:]
        if clean_raw.endswith("```"):
            clean_raw = clean_raw[:-3]
        
        try:
            parsed_json = json.loads(clean_raw.strip())
            repaired = True
        except:
            pass

    if parsed_json and isinstance(parsed_json, dict):
        # 2. Key check
        keys = set(parsed_json.keys())
        missing = SCHEMA_KEYS - keys
        extra = keys - SCHEMA_KEYS
        if missing:
            errors.append(f"Missing keys: {missing}")
        if extra:
            errors.append(f"Extra keys: {extra}")
        
        # 3. Enum check
        if "severity" in parsed_json:
            if parsed_json["severity"] not in SEVERITY_VALUES:
                errors.append(f"Invalid severity: {parsed_json['severity']}")
        
        # 4. Type check
        if "entities" in parsed_json:
            if not isinstance(parsed_json["entities"], list):
                errors.append("Entities is not a list")

        if not missing and not extra and not errors and not repaired:
            valid = True
            
        if not missing and not extra and not (set(errors) - {e for e in errors if "JSON Parse Error" in e}) and repaired:
            # It was repaired successfully
            valid = False
    else:
        if not errors:
            errors.append("Root is not a JSON object")

    return valid, repaired, errors

def main():
    hypothesis_path = r"D:\Mind\Predictions\approved\HYPOTHESIS_JSON_001.json"
    fixtures_path = r"D:\Mind\Laboratory\Hypotheses\HYP_006\fixtures.json"
    obs_dir = r"D:\Mind\Laboratory\observations"
    hyp_dir = r"D:\Mind\Laboratory\Hypotheses\HYP_006"
    
    with open(fixtures_path, "r") as f:
        fixtures_raw = f.read()
        fixtures = json.loads(fixtures_raw)
    
    fixture_hash = sha256_hash(fixtures_raw)

    prompt_a_template = """Extract the incident_id, event_type, severity, entities, occurred_utc, and summary from the following text.
Severity must be LOW, MEDIUM, or HIGH. If occurred_utc is unknown, output null. Entities must be a list of strings.
Output the data using keys 'incident_id', 'event_type', 'severity', 'entities', 'occurred_utc', 'summary'.
Format the output carefully.

Text: {text}"""

    prompt_b_template = """Extract information from the following text and return ONLY a JSON object that strictly conforms to this schema:
{{
  "incident_id": "string",
  "event_type": "string",
  "severity": "LOW | MEDIUM | HIGH",
  "entities": ["string"],
  "occurred_utc": "ISO-8601 string or null",
  "summary": "string"
}}
Do not include any other text or markdown outside the JSON object.

Text: {text}"""

    results_a = []
    results_b = []
    artifacts = []

    for idx, fixture in enumerate(fixtures):
        text = fixture["text"]
        
        # Alternate order
        if idx % 2 == 0:
            order = [("natural_language", prompt_a_template, results_a), ("explicit_json_schema", prompt_b_template, results_b)]
        else:
            order = [("explicit_json_schema", prompt_b_template, results_b), ("natural_language", prompt_a_template, results_a)]

        for condition, template, res_list in order:
            prompt = template.format(text=text)
            prompt_hash = sha256_hash(prompt)
            input_hash = sha256_hash(text)
            
            started = datetime.now(timezone.utc).isoformat()
            raw_output, latency = query_ollama(prompt)
            completed = datetime.now(timezone.utc).isoformat()
            
            valid, repaired, errors = validate_schema(raw_output)
            
            artifact = {
                "trial_id": idx + 1,
                "pair_id": f"FIX_{idx+1}",
                "condition": condition,
                "fixture_hash": fixture_hash,
                "input_hash": input_hash,
                "prompt_hash": prompt_hash,
                "model": MODEL,
                "temperature": TEMPERATURE,
                "started_utc": started,
                "completed_utc": completed,
                "latency_ms": latency,
                "raw_output": raw_output,
                "schema_valid": valid,
                "repairable": repaired,
                "validation_errors": errors
            }
            artifacts.append(artifact)
            res_list.append(valid)
            
            # Save raw artifact
            safe_cond = condition.replace(" ", "_").lower()
            artifact_file = os.path.join(hyp_dir, f"TRIAL_{idx+1}_{safe_cond}.json")
            with open(artifact_file, "w") as f:
                json.dump(artifact, f, indent=4)
                
    a_pass_rate = sum(results_a) / len(results_a)
    b_pass_rate = sum(results_b) / len(results_b)
    
    diff = b_pass_rate - a_pass_rate
    
    if diff < 0.20:
        conclusion = "UNSUPPORTED"
        if b_pass_rate <= a_pass_rate:
            conclusion = "CONTRADICTED"
    else:
        conclusion = "SUPPORTED"

    agg_result = {
        "hypothesis_id": "HYP_006",
        "condition_A_natural_language_validity_rate": a_pass_rate,
        "condition_B_explicit_json_schema_validity_rate": b_pass_rate,
        "difference": diff,
        "conclusion": conclusion,
        "total_trials": len(fixtures),
        "total_calls": len(artifacts)
    }
    
    agg_file = os.path.join(hyp_dir, "aggregate_result.json")
    with open(agg_file, "w") as f:
        json.dump(agg_result, f, indent=4)
        
    print(json.dumps(agg_result, indent=4))
    
    # Emit LAB_OBS
    obs_id = datetime.now(timezone.utc).strftime("LAB_OBS_%Y%m%d_%H%M%S")
    obs_path = os.path.join(obs_dir, f"{obs_id}.json")
    
    lab_obs = {
        "observation_id": obs_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_agent": "AntiGravity",
        "event_type": "EXPERIMENT_COMPLETED",
        "evidence_type": "EMPIRICAL_TRIAL",
        "confidence": 99,
        "tags": ["structured_output", "ollama", "HYP_006"],
        "payload": agg_result,
        "artifacts_refs": [
            os.path.join(hyp_dir, f"TRIAL_{i+1}_{c}.json") 
            for i in range(10) for c in ["natural_language", "explicit_json_schema"]
        ]
    }
    
    with open(obs_path, "w") as f:
        json.dump(lab_obs, f, indent=4)
        
    print(f"Emitted observation {obs_id}")

if __name__ == "__main__":
    main()
