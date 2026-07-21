import json
import os
import argparse
import sys

VALID_INVARIANTS = {"delta", "isolation", "memory_growth", "memory_coherence"}

def lint_contract(experiment_id, experiments_dir):
    exp_dir = os.path.join(experiments_dir, experiment_id)
    contract_file = os.path.join(exp_dir, "contract.json")
    out_file = os.path.join(exp_dir, "contract_lint_result.json")
    
    def finish(status, allow_run, error_list):
        result = {
            "contract_status": status,
            "model_run_allowed": allow_run,
            "errors": error_list
        }
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
            
        if not allow_run:
            print("CONTRACT_INVALID")
            print("model not run")
            print("validator not run")
            print("verifier not run")
            for err in error_list:
                print(f"- {err}")
            sys.exit(1)
        else:
            print("CONTRACT_VALID")
            sys.exit(0)
    
    if not os.path.isfile(contract_file):
        finish("CONTRACT_INVALID", False, ["No contract.json found."])
        
    try:
        with open(contract_file, 'r', encoding='utf-8') as f:
            contract = json.load(f)
    except Exception as e:
        finish("CONTRACT_INVALID", False, [f"Failed to parse JSON: {e}"])
        
    errors = []
    
    # 1. Missing contract_version
    if "contract_version" not in contract:
        errors.append("contract_version missing")
        
    # 2. Missing required keys
    required_keys = ["method", "signature", "required_calls", "required_fields", "memory_keys", "required_state_mutations", "behavior"]
    for key in required_keys:
        if key not in contract:
            errors.append(f"Missing required key: {key}")
            
    # 3. Signature mismatch
    method = contract.get("method", "")
    sig = contract.get("signature", "")
    if method and sig and f"def {method}" not in sig:
        errors.append(f"signature mismatch: '{sig}' does not match method '{method}'")
        
    # 4. required_state_mutations not reflected in behavior.update_rule
    mutations = contract.get("required_state_mutations", [])
    update_rule = contract.get("behavior", {}).get("update_rule", "")
    
    for mut in mutations:
        mut_clean = "".join(mut.split())
        rule_clean = "".join(update_rule.split())
        if mut_clean not in rule_clean:
            errors.append(f"required_state_mutations not reflected in behavior.update_rule: '{mut}'")

    # 5. Invariants checks
    invariants = contract.get("invariants", [])
    seen_types = set()
    for inv in invariants:
        inv_type = inv.get("type")
        if not inv_type:
            errors.append("Malformed invariant entry: missing 'type'")
            continue
            
        if inv_type not in VALID_INVARIANTS:
            errors.append(f"Unknown invariant type: {inv_type}")
            
        if inv_type in seen_types:
            errors.append(f"Duplicate invariant entry: {inv_type}")
        seen_types.add(inv_type)
        
    # 6. invariant requires fields not listed in memory_keys
    mem_keys = contract.get("memory_keys", [])
    if "memory_coherence" in seen_types or "delta" in seen_types:
        required_mem_keys = {"reward", "delta", "old_score", "new_score"}
        missing = required_mem_keys - set(mem_keys)
        if missing:
            errors.append(f"Invariant requires fields not listed in memory_keys: {missing}")

    if errors:
        finish("CONTRACT_INVALID", False, errors)
    else:
        finish("CONTRACT_VALID", True, [])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lint contract.json for coherence before running.")
    parser.add_argument("experiment_id", help="The ID of the experiment")
    parser.add_argument("--dir", default=r"D:\Mind\Laboratory\Experiments", help="Base directory")
    args = parser.parse_args()
    
    lint_contract(args.experiment_id, args.dir)
