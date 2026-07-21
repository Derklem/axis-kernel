import os
import json
import sys

GENERATOR_VERSION = "2.0.0"

def generate_prompt(experiment_id, experiments_dir=r"D:\Mind\Laboratory\Experiments", attempt=1):
    exp_dir = os.path.join(experiments_dir, experiment_id)
    contract_file = os.path.join(exp_dir, "contract.json")
    
    attempt_dir = os.path.join(exp_dir, f"attempt_{attempt}")
    os.makedirs(attempt_dir, exist_ok=True)
    prompt_file = os.path.join(attempt_dir, "prompt.md")
    
    if not os.path.exists(contract_file):
        print(f"Error: contract.json not found for {experiment_id}")
        sys.exit(1)
        
    with open(contract_file, 'r', encoding='utf-8') as f:
        contract = json.load(f)
        
    method = contract.get("method", "function")
    signature = contract.get("signature", "def function():")
    context = contract.get("behavior", {}).get("context", "")
    update_rule = contract.get("behavior", {}).get("update_rule", "")
    harness = contract.get("harness_contract", "")
    
    req_calls = contract.get("required_calls", [])
    req_fields = contract.get("required_fields", [])
    mem_keys = contract.get("memory_keys", [])
    req_mutations = contract.get("required_state_mutations", [])
    
    prompt = f"Task: Modify the behavior according to the strict contract below.\n\n"
    
    prompt += "IMPORTANT CONTEXT:\n"
    prompt += f"{context}\n\n"
    
    prompt += f"REQUIREMENTS FOR `{signature}`:\n"
    for call in req_calls:
        prompt += f"- Must call `{call}`\n"
    for field in req_fields:
        prompt += f"- Must use/preserve `{field}`\n"
        
    if mem_keys:
        prompt += f"- Appended memory must contain exactly these keys: {', '.join(mem_keys)}\n"
        
    for mut in req_mutations:
        prompt += f"- Must explicitly mutate state: `{mut}`\n"
        
    prompt += f"\nHARNESS CONTRACT:\n{harness}\n\n"
    
    prompt += f"REQUIRED LOGIC RULE:\n{update_rule}\n\n"
    
    prompt += f"OUTPUT CONTRACT:\n"
    prompt += f"Return exactly one complete Python method.\n"
    prompt += f"The first non-empty line must be:\n\n"
    prompt += f"{signature}\n\n"
    prompt += "Do not output only the method body.\n"
    prompt += "Do not output a class.\n"
    prompt += "You MUST wrap the method inside a single ```python markdown block.\n"
    prompt += "Do not output explanation.\n"
    prompt += "The method must be syntactically valid when pasted inside a class.\n"
    
    if attempt == 1 and experiment_id == "RL_011":
        prompt += "\nCRITICAL: You MUST write `new_score = old_score - delta`. Do not use `+`. I repeat, use subtraction. BUT YOU MUST STILL CALL `self.memory.append({...})` with all the required keys! This is a mandatory test of the correction loop.\n"

    
    if attempt > 1:
        correction_input_file = os.path.join(attempt_dir, "correction_input.json")
        if os.path.exists(correction_input_file):
            with open(correction_input_file, 'r', encoding='utf-8') as f:
                corr = json.load(f)
            prompt += f"\n\n--- SELF-CORRECTION (ATTEMPT {attempt}) ---\n"
            prompt += "The previous implementation failed validation.\n"
            prompt += "Below is the previous code and the exact validation failure.\n"
            prompt += "Do NOT explain. Return only the corrected code satisfying the contract.\n\n"
            prompt += f"PREVIOUS CODE:\n```python\n{corr.get('previous_code', '')}\n```\n\n"
            prompt += f"VALIDATION FAILURE:\n```json\n{json.dumps(corr.get('validation_failure', {}), indent=2)}\n```\n\n"

    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
        
    print(f"Prompt generated successfully for {experiment_id} using generator v{GENERATOR_VERSION} (attempt {attempt}).")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_id")
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    generate_prompt(args.experiment_id, attempt=args.attempt)
