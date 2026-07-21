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

class BaseExperimentRunner:
    def __init__(self, model="llama3:latest", temperature=0.0, system_prompt="You are a helpful assistant.", expected_metrics=None):
        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.expected_metrics = expected_metrics or []

    def build_prompt(self, condition: str, fixture: dict) -> str:
        raise NotImplementedError("Subclasses must implement build_prompt")

    def validate_output(self, raw_output: str, fixture: dict, condition: str) -> dict:
        raise NotImplementedError("Subclasses must implement validate_output")

    def summarize_experiment(self, results: dict) -> dict:
        raise NotImplementedError("Subclasses must implement summarize_experiment")

    def run_experiment(self, fixtures_path, hyp_dir, conditions, schedule_orders=None):
        if not os.path.exists(hyp_dir):
            os.makedirs(hyp_dir)
            
        with open(fixtures_path, "r", encoding="utf-8") as f:
            fixtures = json.load(f)
            
        with open(fixtures_path, "rb") as f:
            fixture_hash = hashlib.sha256(f.read()).hexdigest()
        
        initial_metadata = get_model_metadata(self.model)
        
        results = {
            cond: {
                "scheduled_calls": 0, 
                "transport_failures": 0, 
                "completed_model_calls": 0,
                "metrics_sums": {m: 0 for m in self.expected_metrics}, 
                "completed_latencies": [],
                "failed_latencies": []
            } for cond in conditions
        }
        artifacts = []

        for idx, fixture in enumerate(fixtures):
            if schedule_orders:
                conditions_order = schedule_orders[idx % len(schedule_orders)]
            else:
                conditions_order = list(conditions)
                random.shuffle(conditions_order)
                
            execution_order_names = conditions_order

            for order_idx, condition in enumerate(conditions_order):
                preceding_condition = None if order_idx == 0 else conditions_order[order_idx - 1]
                
                results[condition]["scheduled_calls"] += 1
                
                prompt = self.build_prompt(condition, fixture)
                input_hash = hashlib.sha256(json.dumps(fixture, sort_keys=True).encode("utf-8")).hexdigest()
                prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
                
                started = datetime.now(timezone.utc).isoformat()
                q_result = query_ollama(self.model, self.system_prompt, prompt, self.temperature)
                completed = datetime.now(timezone.utc).isoformat()
                
                latency = q_result["latency_ms"]
                
                if not q_result["transport_success"]:
                    results[condition]["transport_failures"] += 1
                    results[condition]["failed_latencies"].append(latency)
                    artifact = {
                        "trial_id": idx + 1,
                        "pair_id": fixture.get("fixture_id", f"FIX_{idx+1}"),
                        "condition": condition,
                        "execution_order": execution_order_names,
                        "execution_position": order_idx + 1,
                        "preceding_condition": preceding_condition,
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
                    results[condition]["completed_latencies"].append(latency)
                    raw_output = q_result["raw_output"]
                    
                    validation = self.validate_output(raw_output, fixture, condition)
                    
                    for metric_name, value in validation.get("metrics", {}).items():
                        if isinstance(value, bool):
                            results[condition]["metrics_sums"][metric_name] = results[condition]["metrics_sums"].get(metric_name, 0) + int(value)

                    artifact = {
                        "trial_id": idx + 1,
                        "pair_id": fixture.get("fixture_id", f"FIX_{idx+1}"),
                        "condition": condition,
                        "execution_order": execution_order_names,
                        "execution_position": order_idx + 1,
                        "preceding_condition": preceding_condition,
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
                        "validation": validation
                    }
                artifacts.append(artifact)
                
                safe_cond = condition.replace(" ", "_").lower()
                artifact_file = os.path.join(hyp_dir, f"TRIAL_{idx+1}_{safe_cond}.json")
                with open(artifact_file, "w") as f:
                    json.dump(artifact, f, indent=4)
                    
        final_metadata = get_model_metadata(self.model)
        
        initial_digest = initial_metadata.get("digest")
        final_digest = final_metadata.get("digest")
        
        if initial_digest is None or final_digest is None:
            identity_verification = "UNVERIFIED"
        elif initial_digest != final_digest:
            identity_verification = "CHANGED"
        else:
            identity_verification = "VERIFIED_STABLE"

        def calc_rates(res):
            completed = res["completed_model_calls"]
            scheduled = res["scheduled_calls"]
            
            rates = {
                "transport_failure_rate": res["transport_failures"] / scheduled if scheduled > 0 else None,
                "mean_completed_call_latency_ms": sum(res["completed_latencies"]) / len(res["completed_latencies"]) if res["completed_latencies"] else None,
                "mean_transport_failure_latency_ms": sum(res["failed_latencies"]) / len(res["failed_latencies"]) if res["failed_latencies"] else None
            }
            
            for metric_name, sum_val in res["metrics_sums"].items():
                rates[f"{metric_name}_rate"] = sum_val / completed if completed > 0 else None
                
            return rates

        agg_result = {
            "hypothesis_id": os.path.basename(hyp_dir),
            "model_metadata_start": initial_metadata,
            "model_metadata_end": final_metadata,
            "model_identity_verification": identity_verification,
        }
        
        if identity_verification != "VERIFIED_STABLE":
            agg_result["run_validity"] = "FLAGGED"
        else:
            agg_result["run_validity"] = "VALID"
            
        for condition in conditions_order:
            agg_result[condition] = {
                "raw_counts": {k: v for k, v in results[condition].items() if k not in ["completed_latencies", "failed_latencies", "metrics_sums"]},
                "metric_counts": results[condition]["metrics_sums"],
                "rates": calc_rates(results[condition])
            }
            
        summary = self.summarize_experiment(agg_result)
        agg_result.update(summary)
        
        agg_file = os.path.join(hyp_dir, "aggregate_result.json")
        with open(agg_file, "w") as f:
            json.dump(agg_result, f, indent=4)
            
        return agg_result, artifacts
