import os
import json
import hashlib
import sys
import re
from datetime import datetime, timezone
from gemma_bridge import query_gemma

LAB_DIR = r"D:\Mind\Laboratory"
EXPERIMENTS_DIR = os.path.join(LAB_DIR, "Experiments")
LEDGER_FILE = os.path.join(LAB_DIR, "ledger.jsonl")
BUNDLES_DIR = os.path.join(LAB_DIR, "research_bundles")
HYPOTHESES_DIR = r"D:\Mind\Hypotheses\active"

def extract_evidence():
    """
    Stage 1: Deterministic Extractor.
    Gathers factual data about experiments without interpretation.
    """
    evidence = {}
    
    # 1. Parse ledger to get experiment final outcomes
    if os.path.exists(LEDGER_FILE):
        with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                entry = json.loads(line)
                exp_id = entry.get("experiment")
                if not exp_id or not exp_id.startswith("RL_"):
                    continue
                
                if exp_id not in evidence:
                    evidence[exp_id] = {"ledger_entries": [], "attempts": {}}
                    
                evidence[exp_id]["ledger_entries"].append(entry)

    # 2. Parse Experiment Directories
    if os.path.exists(EXPERIMENTS_DIR):
        for exp_id in os.listdir(EXPERIMENTS_DIR):
            if not exp_id.startswith("RL_"):
                continue
            
            exp_dir = os.path.join(EXPERIMENTS_DIR, exp_id)
            if not os.path.isdir(exp_dir): continue
            
            if exp_id not in evidence:
                evidence[exp_id] = {"ledger_entries": [], "attempts": {}}
                
            for item in os.listdir(exp_dir):
                if item.startswith("attempt_"):
                    att_dir = os.path.join(exp_dir, item)
                    if not os.path.isdir(att_dir): continue
                    
                    attempt_data = {}
                    val_file = os.path.join(att_dir, "validation_result.json")
                    if os.path.exists(val_file):
                        with open(val_file, 'r', encoding='utf-8') as f:
                            attempt_data["validation"] = json.load(f)
                            
                    eval_file = os.path.join(att_dir, "evaluation.json")
                    if os.path.exists(eval_file):
                        with open(eval_file, 'r', encoding='utf-8') as f:
                            attempt_data["evaluation"] = json.load(f)
                            
                    corr_file = os.path.join(att_dir, "correction_input.json")
                    if os.path.exists(corr_file):
                        with open(corr_file, 'r', encoding='utf-8') as f:
                            attempt_data["correction_input"] = json.load(f)
                            
                    evidence[exp_id]["attempts"][item] = attempt_data

    # Save Bundle
    bundle_id = "RB_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bundle_content = json.dumps({"bundle_id": bundle_id, "evidence": evidence}, sort_keys=True)
    evidence_hash = hashlib.sha256(bundle_content.encode('utf-8')).hexdigest()
    
    bundle_data = {
        "bundle_id": bundle_id,
        "evidence_hash": evidence_hash,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "evidence": evidence
    }
    
    bundle_path = os.path.join(BUNDLES_DIR, f"{bundle_id}.json")
    with open(bundle_path, 'w', encoding='utf-8') as f:
        json.dump(bundle_data, f, indent=4)
        
    print(f"Evidence bundle created: {bundle_id}")
    return bundle_id, evidence_hash, evidence

def synthesize_hypothesis(bundle_id, evidence_hash, evidence):
    """
    Stage 2: Gemma Hypothesis Synthesizer.
    """
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
    
    print("Querying Gemma for synthesis...")
    response_text = query_gemma(prompt)
    
    # Strip markdown blocks if it hallucinated them despite instructions
    response_text = re.sub(r'^```(json)?', '', response_text, flags=re.MULTILINE)
    response_text = re.sub(r'```$', '', response_text, flags=re.MULTILINE).strip()
    
    try:
        hypothesis_json = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"Failed to parse Gemma output as JSON: {e}")
        print("Raw output:")
        print(response_text)
        sys.exit(1)
        
    return hypothesis_json

def validate_and_save_hypothesis(bundle_id, evidence_hash, evidence, hyp_data):
    """
    Stage 3: Schema Validation.
    """
    required_keys = ["observation", "hypothesis", "confidence", "evidence", "counterexamples", 
                     "recommended_experiment", "falsification_condition"]
                     
    for key in required_keys:
        if key not in hyp_data:
            print(f"Schema Validation Failed: Missing key '{key}'")
            sys.exit(1)
            
    # Check for fabricated evidence lineage
    for exp in hyp_data.get("evidence", []):
        if exp not in evidence:
            print(f"Schema Validation Failed: Hallucinated evidence ID '{exp}' not found in bundle.")
            sys.exit(1)
            
    for exp in hyp_data.get("counterexamples", []):
        if exp not in evidence:
            print(f"Schema Validation Failed: Hallucinated counterexample ID '{exp}' not found in bundle.")
            sys.exit(1)
            
    hyp_id = "HYP_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    final_hyp = {
        "id": hyp_id,
        "status": "active",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "observation": hyp_data["observation"],
        "hypothesis": hyp_data["hypothesis"],
        "confidence": float(hyp_data["confidence"]),
        "evidence": hyp_data["evidence"],
        "counterexamples": hyp_data["counterexamples"],
        "recommended_experiment": hyp_data["recommended_experiment"],
        "falsification_condition": hyp_data["falsification_condition"],
        "source_engine": "research_engine.py",
        "model_used": "gemma3:4b",
        "evidence_bundle_id": bundle_id,
        "evidence_hash": evidence_hash
    }
    
    hyp_path = os.path.join(HYPOTHESES_DIR, f"{hyp_id}.json")
    with open(hyp_path, 'w', encoding='utf-8') as f:
        json.dump(final_hyp, f, indent=4)
        
    print(f"Hypothesis validated and saved: {hyp_id}")
    return hyp_path

if __name__ == "__main__":
    bundle_id, ev_hash, evidence = extract_evidence()
    raw_hyp = synthesize_hypothesis(bundle_id, ev_hash, evidence)
    validate_and_save_hypothesis(bundle_id, ev_hash, evidence, raw_hyp)
