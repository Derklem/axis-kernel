import os
import json
import hashlib
import sys
import re
from datetime import datetime, timezone
from gemma_bridge import query_gemma

LAB_DIR = r"D:\Mind\Laboratory"
BUNDLES_DIR = os.path.join(LAB_DIR, "research_bundles")
CALIBRATION_DIR = r"D:\Mind\Calibration\laboratory"
TARGET_BUNDLE = "RB_20260702_043556"
BUNDLE_PATH = os.path.join(BUNDLES_DIR, f"{TARGET_BUNDLE}.json")

def load_bundle():
    if not os.path.exists(BUNDLE_PATH):
        print(f"Error: Target bundle {BUNDLE_PATH} not found.")
        sys.exit(1)
    with open(BUNDLE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_synthesis(evidence, temperature):
    prompt = "You are the Research Engine of an autonomous AI laboratory.\n"
    prompt += "Your job is to read the raw deterministic evidence bundle of past experiments and propose a testable hypothesis about the model's behavior.\n"
    prompt += "Look for repeated patterns in validation notes, correction attempts, or specific mathematical failures.\n\n"
    
    prompt += "EVIDENCE BUNDLE:\n"
    prompt += json.dumps(evidence, indent=2) + "\n\n"
    
    prompt += "OUTPUT SCHEMA (JSON ONLY):\n"
    prompt += "{\n"
    prompt += '  "observation": "What pattern did you notice across multiple experiments?",\n'
    prompt += '  "hypothesis": "What is the underlying explanation for this behavior?",\n'
    prompt += '  "confidence": 0.0 to 1.0 float,\n'
    prompt += '  "evidence": ["RL_XXX", "RL_YYY"],\n'
    prompt += '  "counterexamples": ["RL_ZZZ"],\n'
    prompt += '  "recommended_experiment": "What experiment should we run next to test this?",\n'
    prompt += '  "falsification_condition": "If X occurs, this hypothesis is definitively proven false."\n'
    prompt += "}\n\n"
    prompt += "Return ONLY a valid JSON object matching this schema. Do not use markdown fences. Do not output anything outside the JSON block."
    
    print(f"Querying Gemma with temperature {temperature}...")
    response_text = query_gemma(prompt, temperature=temperature)
    
    # Hash raw response
    raw_hash = hashlib.sha256(response_text.encode('utf-8')).hexdigest()
    
    # Clean output
    cleaned_text = re.sub(r'^```(json)?', '', response_text, flags=re.MULTILINE)
    cleaned_text = re.sub(r'```$', '', cleaned_text, flags=re.MULTILINE).strip()
    
    try:
        hypothesis_json = json.loads(cleaned_text)
        is_valid = validate_schema(evidence, hypothesis_json)
        return True, hypothesis_json, raw_hash
    except json.JSONDecodeError:
        return False, None, raw_hash

def validate_schema(evidence, hyp_data):
    required_keys = ["observation", "hypothesis", "confidence", "evidence", "counterexamples", 
                     "recommended_experiment", "falsification_condition"]
    for key in required_keys:
        if key not in hyp_data:
            return False
            
    for exp in hyp_data.get("evidence", []):
        if exp not in evidence:
            return False
            
    for exp in hyp_data.get("counterexamples", []):
        if exp not in evidence:
            return False
            
    return True

if __name__ == "__main__":
    os.makedirs(CALIBRATION_DIR, exist_ok=True)
    
    bundle_data = load_bundle()
    evidence = bundle_data.get("evidence", {})
    
    # The 4-pass pilot
    run_configs = [
        {"temp": 0.0, "run": 1},
        {"temp": 0.0, "run": 2},
        {"temp": 0.5, "run": 1},
        {"temp": 0.5, "run": 2},
    ]
    
    reports = []
    
    for config in run_configs:
        temp = config["temp"]
        run_idx = config["run"]
        
        valid_schema, hyp_data, raw_hash = run_synthesis(evidence, temp)
        
        report = {
            "bundle_id": TARGET_BUNDLE,
            "temperature": temp,
            "run_index": run_idx,
            "raw_response_hash": raw_hash,
            "valid_schema": valid_schema,
            "hypothesis_hash": None,
            "evidence_ids": [],
            "confidence": 0.0,
            "recommended_experiment": "",
            "falsification_condition": ""
        }
        
        if valid_schema and hyp_data:
            # Hash the cleaned JSON content for easy comparison
            hyp_str = json.dumps(hyp_data, sort_keys=True)
            report["hypothesis_hash"] = hashlib.sha256(hyp_str.encode('utf-8')).hexdigest()
            
            report["evidence_ids"] = hyp_data.get("evidence", [])
            report["confidence"] = float(hyp_data.get("confidence", 0.0))
            report["observation"] = hyp_data.get("observation", "")
            report["hypothesis"] = hyp_data.get("hypothesis", "")
            report["recommended_experiment"] = hyp_data.get("recommended_experiment", "")
            report["falsification_condition"] = hyp_data.get("falsification_condition", "")
            
            # Save the full hypothesis for manual inspection
            hyp_id = f"HYP_META_{temp}_{run_idx}"
            report["hypothesis_id"] = hyp_id
            with open(os.path.join(CALIBRATION_DIR, f"{hyp_id}.json"), 'w', encoding='utf-8') as f:
                json.dump(hyp_data, f, indent=4)
                
        reports.append(report)
        print(f"Finished Run {run_idx} at Temp {temp}. Valid Schema: {valid_schema}")

    # Output aggregated pilot report
    pilot_report_path = os.path.join(CALIBRATION_DIR, "pilot_report_001.json")
    with open(pilot_report_path, 'w', encoding='utf-8') as f:
        json.dump(reports, f, indent=4)
        
    print(f"Meta-Calibration Pilot Complete. Report saved to {pilot_report_path}")
