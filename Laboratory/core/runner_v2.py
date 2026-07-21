import os
import json
import hashlib
import urllib.request
import urllib.error
import time
from datetime import datetime, timezone
import uuid

OLLAMA_GENERATE_API = "http://localhost:11434/api/generate"
OLLAMA_TAGS_API = "http://localhost:11434/api/tags"

SCHEMA_KEYS = {"incident_id", "event_type", "severity", "entities", "occurred_utc", "summary"}
SEVERITY_VALUES = {"LOW", "MEDIUM", "HIGH"}
EPSILON = 1e-12

def sha256_hash(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def get_model_metadata(model_name: str) -> dict:
    try:
        req = urllib.request.Request(OLLAMA_TAGS_API)
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            for m in result.get("models", []):
                if m.get("name") == model_name or m.get("model") == model_name:
                    return {
                        "digest": m.get("digest"),
                        "size": m.get("size"),
                        "quantization_level": m.get("details", {}).get("quantization_level")
                    }
    except Exception as e:
        print(f"Failed to fetch model metadata: {e}")
    return {}

def query_ollama(model: str, system_prompt: str, prompt: str, temperature: float) -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "temperature": temperature,
        "stream": False,
        "options": {
            "num_predict": 500
        }
    }
    req = urllib.request.Request(OLLAMA_GENERATE_API, data=json.dumps(payload).encode('utf-8'),
                                 headers={'Content-Type': 'application/json'})
    start = time.time()
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            latency = (time.time() - start) * 1000
            return {
                "transport_success": True,
                "raw_output": result.get("response", ""),
                "latency_ms": latency
            }
    except Exception as e:
        latency = (time.time() - start) * 1000
        return {
            "transport_success": False,
            "error": str(e),
            "latency_ms": latency
        }

def is_iso8601_utc_or_offset(value: object) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False

    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False

    return parsed.tzinfo is not None

def validate_schema(raw: str):
    valid = False
    repaired = False
    errors = []
    parsed_json = None
    
    try:
        parsed_json = json.loads(raw)
    except json.JSONDecodeError as e:
        errors.append(f"JSON Parse Error: {e}")
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
        keys = set(parsed_json.keys())
        missing = SCHEMA_KEYS - keys
        extra = keys - SCHEMA_KEYS
        if missing:
            errors.append(f"Missing keys: {missing}")
        if extra:
            errors.append(f"Extra keys: {extra}")
        
        if "severity" in parsed_json:
            if parsed_json["severity"] not in SEVERITY_VALUES:
                errors.append(f"Invalid severity: {parsed_json['severity']}")
        
        if "entities" in parsed_json:
            if not isinstance(parsed_json["entities"], list):
                errors.append("Entities is not a list")
            else:
                for idx, ent in enumerate(parsed_json["entities"]):
                    if not isinstance(ent, str):
                        errors.append(f"Entity at index {idx} is not a string")
        
        if "occurred_utc" in parsed_json:
            if not is_iso8601_utc_or_offset(parsed_json["occurred_utc"]):
                errors.append(f"Invalid ISO-8601 UTC timestamp: {parsed_json['occurred_utc']}")

        if not missing and not extra and not errors and not repaired:
            valid = True
            
        if not missing and not extra and not set(errors) - {e for e in errors if "JSON Parse Error" in e} and repaired:
            valid = False
    else:
        if not errors:
            errors.append("Root is not a JSON object")

    return valid, repaired, errors

class ExperimentRunner:
    def __init__(self, model="llama3:latest", temperature=0.0):
        self.model = model
        self.temperature = temperature
        self.system_prompt = "You are a helpful assistant."
        self.prompt_a_template = """Extract the incident_id, event_type, severity, entities, occurred_utc, and summary from the following text.
Severity must be LOW, MEDIUM, or HIGH. If occurred_utc is unknown, output null. Entities must be a list of strings.
Output the data using keys 'incident_id', 'event_type', 'severity', 'entities', 'occurred_utc', 'summary'.
Format the output carefully.

Text: {text}"""

        self.prompt_b_template = """Extract information from the following text and return ONLY a JSON object that strictly conforms to this schema:
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

    def run_experiment(self, fixtures_path, hyp_dir):
        if not os.path.exists(hyp_dir):
            os.makedirs(hyp_dir)
            
        with open(fixtures_path, "r") as f:
            fixtures_raw = f.read()
            fixtures = json.loads(fixtures_raw)
        
        fixture_hash = sha256_hash(fixtures_raw)
        
        initial_metadata = get_model_metadata(self.model)
        
        results = {
            "natural_language": {"scheduled_calls": 0, "transport_failures": 0, "completed_model_calls": 0, "valid_outputs": 0, "repairs": 0, "latencies": []},
            "explicit_json_schema": {"scheduled_calls": 0, "transport_failures": 0, "completed_model_calls": 0, "valid_outputs": 0, "repairs": 0, "latencies": []}
        }
        artifacts = []

        for idx, fixture in enumerate(fixtures):
            text = fixture["text"]
            
            if idx % 2 == 0:
                order = [("natural_language", self.prompt_a_template), ("explicit_json_schema", self.prompt_b_template)]
            else:
                order = [("explicit_json_schema", self.prompt_b_template), ("natural_language", self.prompt_a_template)]
                
            execution_order_names = [o[0] for o in order]

            for condition, template in order:
                results[condition]["scheduled_calls"] += 1
                
                prompt = template.format(text=text)
                prompt_hash = sha256_hash(prompt)
                input_hash = sha256_hash(text)
                
                started = datetime.now(timezone.utc).isoformat()
                q_result = query_ollama(self.model, self.system_prompt, prompt, self.temperature)
                completed = datetime.now(timezone.utc).isoformat()
                
                latency = q_result["latency_ms"]
                results[condition]["latencies"].append(latency)
                
                if not q_result["transport_success"]:
                    results[condition]["transport_failures"] += 1
                    artifact = {
                        "trial_id": idx + 1,
                        "pair_id": fixture.get("fixture_id", f"FIX_{idx+1}"),
                        "condition": condition,
                        "execution_order": execution_order_names,
                        "fixture_hash": fixture_hash,
                        "input_hash": input_hash,
                        "prompt_hash": prompt_hash,
                        "model": self.model,
                        "model_digest": initial_metadata.get("digest"),
                        "temperature": self.temperature,
                        "started_utc": started,
                        "completed_utc": completed,
                        "latency_ms": latency,
                        "transport_success": False,
                        "transport_error": q_result.get("error", "Unknown"),
                    }
                else:
                    results[condition]["completed_model_calls"] += 1
                    raw_output = q_result["raw_output"]
                    valid, repaired, errors = validate_schema(raw_output)
                    
                    if valid:
                        results[condition]["valid_outputs"] += 1
                    if repaired:
                        results[condition]["repairs"] += 1
                        
                    artifact = {
                        "trial_id": idx + 1,
                        "pair_id": fixture.get("fixture_id", f"FIX_{idx+1}"),
                        "condition": condition,
                        "execution_order": execution_order_names,
                        "fixture_hash": fixture_hash,
                        "input_hash": input_hash,
                        "prompt_hash": prompt_hash,
                        "model": self.model,
                        "model_digest": initial_metadata.get("digest"),
                        "temperature": self.temperature,
                        "started_utc": started,
                        "completed_utc": completed,
                        "latency_ms": latency,
                        "transport_success": True,
                        "raw_output": raw_output,
                        "schema_valid": valid,
                        "deterministically_repairable": repaired,
                        "validation_errors": errors
                    }
                artifacts.append(artifact)
                
                safe_cond = condition.replace(" ", "_").lower()
                artifact_file = os.path.join(hyp_dir, f"TRIAL_{idx+1}_{safe_cond}.json")
                with open(artifact_file, "w") as f:
                    json.dump(artifact, f, indent=4)
                    
        final_metadata = get_model_metadata(self.model)
        model_identity_changed = initial_metadata.get("digest") != final_metadata.get("digest")

        def calc_rates(res):
            completed = res["completed_model_calls"]
            scheduled = res["scheduled_calls"]
            return {
                "validity_rate": res["valid_outputs"] / completed if completed > 0 else 0.0,
                "repairability_rate": res["repairs"] / completed if completed > 0 else 0.0,
                "transport_failure_rate": res["transport_failures"] / scheduled if scheduled > 0 else 0.0,
                "mean_latency_ms": sum(res["latencies"]) / len(res["latencies"]) if res["latencies"] else 0.0,
                "end_to_end_success_rate": res["valid_outputs"] / scheduled if scheduled > 0 else 0.0
            }

        rates_a = calc_rates(results["natural_language"])
        rates_b = calc_rates(results["explicit_json_schema"])
        
        effect = rates_b["validity_rate"] - rates_a["validity_rate"]
        
        if effect >= 0.20:
            conclusion = "SUPPORTED"
        elif effect > EPSILON:
            conclusion = "WEAK_SUPPORT"
        elif abs(effect) <= EPSILON:
            conclusion = "NO_EFFECT"
        else:
            conclusion = "CONTRADICTED"

        agg_result = {
            "hypothesis_id": os.path.basename(hyp_dir),
            "model_metadata": initial_metadata,
            "model_identity_changed_during_run": model_identity_changed,
            "condition_A_natural_language": {
                "raw_counts": results["natural_language"],
                "rates": rates_a
            },
            "condition_B_explicit_json_schema": {
                "raw_counts": results["explicit_json_schema"],
                "rates": rates_b
            },
            "difference": effect,
            "conclusion": conclusion
        }
        
        agg_file = os.path.join(hyp_dir, "aggregate_result.json")
        with open(agg_file, "w") as f:
            json.dump(agg_result, f, indent=4)
            
        return agg_result, artifacts

if __name__ == "__main__":
    pass
