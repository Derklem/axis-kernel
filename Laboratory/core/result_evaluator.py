import os
import json
from datetime import datetime, timezone
import ast

MIND_DIR = r"D:\Mind"
SANDBOX_RESULTS_DIR = os.path.join(MIND_DIR, "Laboratory", "sandbox_results")
EVAL_DIR = os.path.join(MIND_DIR, "Evaluations")

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_latest_result() -> str:
    if not os.path.exists(SANDBOX_RESULTS_DIR):
        return ""
    results = [f for f in os.listdir(SANDBOX_RESULTS_DIR) if f.startswith("EXPERIMENT_RESULT_") and f.endswith(".json")]
    if not results:
        return ""
    results.sort(reverse=True)
    return os.path.join(SANDBOX_RESULTS_DIR, results[0])

def main():
    os.makedirs(EVAL_DIR, exist_ok=True)
    
    result_path = get_latest_result()
    if not result_path:
        print("No sandbox result found.")
        return
        
    result = load_json(result_path)
    
    aggregate = result.get("aggregate_results", {})
    
    true_failure_rate = None
    false_failure_rate = None
    
    # We parse the condition strings back into dicts to find true/false for delta_clamp_enabled
    for cond_str, stats in aggregate.items():
        try:
            # Safely evaluate the string representation of the dictionary
            cond_dict = ast.literal_eval(cond_str)
            if "delta_clamp_enabled" in cond_dict:
                if cond_dict["delta_clamp_enabled"] is True:
                    true_failure_rate = stats.get("failure_rate", 0.0)
                elif cond_dict["delta_clamp_enabled"] is False:
                    false_failure_rate = stats.get("failure_rate", 0.0)
        except Exception:
            pass
            
    if true_failure_rate is None or false_failure_rate is None:
        raise ValueError("Could not extract failure rates for true and false conditions of delta_clamp_enabled.")
        
    effect_size = false_failure_rate - true_failure_rate
    
    interpretation = ""
    if effect_size >= 0.30:
        interpretation = "supports_hypothesis"
    elif 0.10 <= effect_size < 0.30:
        interpretation = "weak_support"
    elif -0.10 < effect_size < 0.10:
        interpretation = "inconclusive"
    else:
        interpretation = "contradicts_hypothesis"
        
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    eval_id = f"EVAL_{timestamp}"
    
    classification_rule = {
        "supports_hypothesis": "effect_size >= 0.30",
        "weak_support": "0.10 <= effect_size < 0.30",
        "inconclusive": "-0.10 < effect_size < 0.10",
        "contradicts_hypothesis": "effect_size <= -0.10"
    }
    
    eval_artifact = {
        "id": eval_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_result": result["id"],
        "source_manifest": result["source_manifest"],
        "source_experiment": result["source_experiment"],
        "source_hypothesis": result.get("source_hypothesis", "unknown"),
        
        "evaluation_status": "complete",
        "effect_size": effect_size,
        "condition_comparison": {
            "false_condition_failure_rate": false_failure_rate,
            "true_condition_failure_rate": true_failure_rate
        },
        "classification_rule": classification_rule,
        "interpretation": interpretation,
        "promotion_allowed": False,  # Hardcoded false until Phase 8 authorizes belief mutation
        "source_engine": "result_evaluator.py"
    }
    
    eval_path = os.path.join(EVAL_DIR, f"{eval_id}.json")
    save_json(eval_path, eval_artifact)
    print(f"Evaluation completed: {os.path.basename(eval_path)}")
    print(f"Effect Size: {effect_size:.2f} -> {interpretation}")

if __name__ == "__main__":
    main()
