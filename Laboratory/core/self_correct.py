import os
import sys
import json
import subprocess
import re

MAX_ATTEMPTS = 2

def run_self_correction(experiment_id, experiments_dir=r"D:\Mind\Laboratory\Experiments"):
    exp_dir = os.path.join(experiments_dir, experiment_id)
    
    # 1. Preflight Lint
    print(f"--- Running preflight contract lint for {experiment_id} ---")
    res = subprocess.run(["python", r"D:\Mind\Laboratory\core\contract_lint.py", experiment_id])
    if res.returncode != 0:
        print("Preflight failed. Halting.")
        sys.exit(1)
        
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n=== Starting Attempt {attempt} ===")
        attempt_dir = os.path.join(exp_dir, f"attempt_{attempt}")
        os.makedirs(attempt_dir, exist_ok=True)
        
        # 2. Run pipeline
        subprocess.run(["python", r"D:\Mind\Laboratory\core\generator.py", experiment_id, "--attempt", str(attempt)], check=True)
        subprocess.run(["python", r"D:\Mind\Laboratory\core\runner.py", experiment_id, "--attempt", str(attempt)], check=True)
        subprocess.run(["python", r"D:\Mind\Laboratory\core\validation.py", experiment_id, "--attempt", str(attempt)], check=True)
        subprocess.run(["python", r"D:\Mind\Laboratory\core\verification.py", experiment_id, "--attempt", str(attempt)], check=True)
        
        # 3. Evaluate Results
        eval_file = os.path.join(attempt_dir, "evaluation.json")
        if not os.path.isfile(eval_file):
            print(f"Error: No evaluation.json found for attempt {attempt}.")
            break
            
        with open(eval_file, 'r', encoding='utf-8') as f:
            eval_data = json.load(f)
            
        if eval_data.get("validation") == "PASS":
            print(f"Attempt {attempt} PASSED validation.")
            if attempt > 1:
                log_final_result(experiment_id, "PASS_AFTER_CORRECTION", attempt, exp_dir)
            else:
                log_final_result(experiment_id, "PASS", attempt, exp_dir)
            break
            
        if attempt < MAX_ATTEMPTS:
            comp = eval_data.get("compilation")
            spec = eval_data.get("specification")
            val = eval_data.get("validation")
            
            if comp == "PASS" and spec == "PASS" and val == "FAIL":
                print(f"Attempt {attempt} failed validation but passed compilation/spec. Triggering self-correction.")
                prepare_correction_input(exp_dir, attempt, eval_data)
            else:
                print(f"Failure class not eligible for self-correction (Comp: {comp}, Spec: {spec}, Val: {val}). Halting.")
                log_final_result(experiment_id, "FAIL", attempt, exp_dir)
                break
        else:
            print(f"Max attempts ({MAX_ATTEMPTS}) reached. Halting.")
            log_final_result(experiment_id, "FAIL_MAX_ATTEMPTS", attempt, exp_dir)

def prepare_correction_input(exp_dir, current_attempt, eval_data):
    curr_dir = os.path.join(exp_dir, f"attempt_{current_attempt}")
    next_dir = os.path.join(exp_dir, f"attempt_{current_attempt + 1}")
    os.makedirs(next_dir, exist_ok=True)
    
    out_file = os.path.join(curr_dir, "output.md")
    val_file = os.path.join(curr_dir, "validation_result.json")
    
    with open(out_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    code_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)
    raw_code = "\n".join(code_blocks) if code_blocks else ""
    
    with open(val_file, 'r', encoding='utf-8') as f:
        val_data = json.load(f)
        
    correction_input = {
        "validator_version": eval_data.get("validator_version", "unknown"),
        "contract_version": eval_data.get("contract_version", "unknown"),
        "generator_version": eval_data.get("generator_version", "unknown"),
        "attempt": current_attempt,
        "parent_attempt": current_attempt,
        "correction_reason": {
            "eligible": True,
            "rule": "behavioral_validation_only"
        },
        "previous_code": raw_code,
        "validation_failure": val_data
    }
    
    next_input_file = os.path.join(next_dir, "correction_input.json")
    with open(next_input_file, 'w', encoding='utf-8') as f:
        json.dump(correction_input, f, indent=4)
        
def log_final_result(experiment_id, status, total_attempts, exp_dir=None):
    ledger_file = r"D:\Mind\Laboratory\ledger.jsonl"
    from datetime import datetime
    import hashlib
    
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "experiment": experiment_id,
        "summary": "self_correction_loop",
        "total_attempts": total_attempts,
        "final_status": status,
        "human_intervention": False
    }
    
    if total_attempts > 1 and exp_dir:
        correction_input_file = os.path.join(exp_dir, "attempt_2", "correction_input.json")
        if os.path.exists(correction_input_file):
            with open(correction_input_file, 'rb') as f:
                entry["correction_input_sha256"] = hashlib.sha256(f.read()).hexdigest()
    with open(ledger_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + "\n")
    print(f"Final status logged: {status}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run bounded self-correction loop.")
    parser.add_argument("experiment_id", help="The ID of the experiment")
    args = parser.parse_args()
    run_self_correction(args.experiment_id)
