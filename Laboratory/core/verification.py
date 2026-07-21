import os
import sys
import json
import re
import textwrap
from datetime import datetime

def verify_output(experiment_id, experiments_dir=r"D:\Mind\Laboratory\Experiments", ledger_file=r"D:\Mind\Laboratory\ledger.jsonl", attempt=1):
    exp_path = os.path.join(experiments_dir, experiment_id)
    attempt_dir = os.path.join(exp_path, f"attempt_{attempt}") if attempt else exp_path
    output_file = os.path.join(attempt_dir, "output.md")
    eval_file = os.path.join(attempt_dir, "evaluation.json")
    spec_file = os.path.join(exp_path, "experiment.json")
    
    if not os.path.isfile(output_file):
        print(f"Error: output.md not found in {exp_path}")
        sys.exit(1)
        
    with open(output_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    contract_file = os.path.join(exp_path, "contract.json")
    
    spec = None
    legacy_format = False
    if os.path.isfile(contract_file):
        with open(contract_file, 'r', encoding='utf-8') as f:
            spec = json.load(f)
    elif os.path.isfile(spec_file):
        with open(spec_file, 'r', encoding='utf-8') as f:
            spec = json.load(f)
            legacy_format = True
            
    val_result = None
    val_file = os.path.join(attempt_dir, "validation_result.json")
    if os.path.isfile(val_file):
        with open(val_file, 'r', encoding='utf-8') as f:
            val_result = json.load(f)

    metrics = {
        "contract_version": spec.get("contract_version", "unknown") if spec else "unknown",
        "generator_version": "1.0.0" if not legacy_format else "N/A",
        "validator_version": val_result.get("validator_version", "1.0.0") if val_result else "unknown",
        "verifier_version": "3.0.0",
        "legacy_spec_format": legacy_format,
        "representation": "INVALID",
        "compilation": "NOT_RUN",
        "specification": "UNKNOWN",
        "logic": "UNKNOWN",
        "validation": val_result.get("validation_status") if val_result else "NOT_RUN",
        "verifier_confidence": 0.0,
        "manual_review_required": True,
        "notes": []
    }
    
    if val_result:
        if metrics["validation"] == "PASS":
            metrics["logic"] = "PASS"
        elif metrics["validation"] == "FAIL":
            metrics["logic"] = "FAIL"
            
        if val_result.get("notes"):
            metrics["notes"].extend([f"Validation: {n}" for n in val_result["notes"]])
    
    if not spec:
        metrics["notes"].append("No experiment.json found. Cannot evaluate specification.")
        metrics["representation"] = "INVALID"
        save_eval(eval_file, metrics, experiment_id, ledger_file, attempt)
        return

    mode = spec.get("compile_mode", "class_wrapper")
    expected_output = spec.get("expected_output", "full_method")

    # Representation Analysis
    code_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)
    
    if not code_blocks:
        metrics["representation"] = "INVALID"
        metrics["notes"].append("No python code blocks found in output.")
        metrics["verifier_confidence"] = 0.85
        save_eval(eval_file, metrics, experiment_id, ledger_file, attempt)
        return
        
    raw_code = "\n".join(code_blocks)
    
    if mode == "standalone":
        metrics["representation"] = "PASS"
    else:
        metrics["representation"] = "NORMALIZABLE"
        metrics["notes"].append(f"Output was normalizable into {mode} form.")

    # Compilation
    clean_code = textwrap.dedent(raw_code)
    
    if mode == "standalone":
        code_to_compile = clean_code
    elif mode == "class_wrapper":
        indented = textwrap.indent(clean_code, '    ')
        code_to_compile = f"class Dummy:\n{indented}"
    elif mode == "function_wrapper":
        indented = textwrap.indent(clean_code, '    ')
        code_to_compile = f"def wrapper():\n{indented}"
    else:
        metrics["notes"].append(f"Unknown compile mode: {mode}")
        metrics["verifier_confidence"] = 0.5
        save_eval(eval_file, metrics, experiment_id, ledger_file)
        return

    try:
        compile(code_to_compile, '<string>', 'exec')
        metrics["compilation"] = "PASS"
    except SyntaxError as e:
        metrics["compilation"] = "FAIL"
        metrics["notes"].append(f"Syntax error: {str(e)}")
        
    # Specification Check
    all_symbols_ok = True
    
    if legacy_format:
        required = spec.get("required_symbols", [])
        for sym in required:
            if sym not in raw_code:
                all_symbols_ok = False
                metrics["notes"].append(f"Missing required symbol: {sym}")
                
        forbidden = spec.get("forbidden_symbols", [])
        for sym in forbidden:
            if sym in raw_code:
                all_symbols_ok = False
                metrics["notes"].append(f"Forbidden symbol present: {sym}")

        if expected_output == "full_method" and "def grow" not in raw_code:
            metrics["notes"].append("Expected full_method but def grow missing.")
            all_symbols_ok = False
    else:
        req_calls = spec.get("required_calls", [])
        for sym in req_calls:
            if sym not in raw_code:
                all_symbols_ok = False
                metrics["notes"].append(f"Missing required call: {sym}")
                
        req_fields = spec.get("required_fields", [])
        for sym in req_fields:
            if sym not in raw_code:
                all_symbols_ok = False
                metrics["notes"].append(f"Missing required field: {sym}")
                
        mem_keys = spec.get("memory_keys", [])
        for sym in mem_keys:
            if sym not in raw_code:
                all_symbols_ok = False
                metrics["notes"].append(f"Missing required memory key: {sym}")
                
        req_mutations = spec.get("required_state_mutations", [])
        for sym in req_mutations:
            if sym not in raw_code:
                all_symbols_ok = False
                metrics["notes"].append(f"Missing required state mutation: {sym}")
                
        sig = spec.get("signature", "def grow")
        if sig not in raw_code:
            metrics["notes"].append(f"Missing required signature: {sig}")
            all_symbols_ok = False

    if all_symbols_ok:
        metrics["specification"] = "PASS"
    else:
        metrics["specification"] = "FAIL"
        
    metrics["verifier_confidence"] = 1.0 if (metrics["specification"] == "PASS" and metrics["compilation"] == "PASS" and metrics["validation"] == "PASS") else 0.85
    
    # If it failed specification, or compilation, or validation hasn't run, or logic is unknown, manual review should flag
    if (
        metrics["specification"] == "FAIL"
        or metrics["compilation"] == "FAIL"
        or metrics["validation"] == "NOT_RUN"
        or metrics["logic"] == "UNKNOWN"
    ):
        metrics["manual_review_required"] = True
    else:
        metrics["manual_review_required"] = False
        
    save_eval(eval_file, metrics, experiment_id, ledger_file, attempt)

def save_eval(eval_file, metrics, experiment_id, ledger_file, attempt):
    with open(eval_file, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=4)
        
    ledger_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "experiment": experiment_id,
        "attempt": attempt,
        "model": "gemma3:4b", 
        "contract_version": metrics["contract_version"],
        "generator_version": metrics["generator_version"],
        "validator_version": metrics["validator_version"],
        "verifier_version": metrics["verifier_version"],
        "legacy_spec_format": metrics["legacy_spec_format"],
        "representation": metrics["representation"],
        "compilation": metrics["compilation"],
        "specification": metrics["specification"],
        "logic": metrics["logic"],
        "validation": metrics["validation"]
    }
    
    with open(ledger_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(ledger_entry) + "\n")
        
    print(f"Verification complete. Results saved to {eval_file}")
    print(json.dumps(metrics, indent=4))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run deterministic verification on experiment output.")
    parser.add_argument("experiment_id", help="The ID of the experiment (e.g., RL_001)")
    parser.add_argument("--attempt", type=int, default=1, help="The attempt number")
    args = parser.parse_args()
    
    verify_output(args.experiment_id, attempt=args.attempt)
