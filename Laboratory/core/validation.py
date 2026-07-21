import json
import os
import re
import textwrap

def run_validation(experiment_id, experiments_dir, attempt=1):
    exp_dir = os.path.join(experiments_dir, experiment_id)
    attempt_dir = os.path.join(exp_dir, f"attempt_{attempt}") if attempt else exp_dir
    output_file = os.path.join(attempt_dir, "output.md")
    spec_file = os.path.join(exp_dir, "experiment.json")
    val_file = os.path.join(attempt_dir, "validation_result.json")
    contract_file = os.path.join(exp_dir, "contract.json")
    
    with open(output_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    spec = None
    is_contract = False
    if os.path.isfile(contract_file):
        with open(contract_file, 'r', encoding='utf-8') as f:
            spec = json.load(f)
            spec["compile_mode"] = spec.get("compile_mode", "class_wrapper")
            is_contract = True
    elif os.path.isfile(spec_file):
        with open(spec_file, 'r', encoding='utf-8') as f:
            spec = json.load(f)

    validator_version = "3.0.0" if is_contract else "2.0.0"

    if spec is None:
        write_result(val_file, "FAIL", ["No experiment.json or contract.json found."], "unknown")
        return

    code_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)
    if not code_blocks:
        write_result(val_file, "NOT_RUN", ["No code block to validate."], validator_version)
        return
        
    raw_code = "\n".join(code_blocks)
    clean_code = textwrap.dedent(raw_code)
    
    if spec.get("compile_mode") == "class_wrapper":
        indented = textwrap.indent(clean_code, '    ')
        code_to_compile = f"class GeneratedDummy:\n{indented}"
    else:
        write_result(val_file, "NOT_RUN", ["Unsupported compile mode for this specific validation."], validator_version)
        return

    # Compile the code
    local_env = {}
    try:
        compile(code_to_compile, '<string>', 'exec')
        exec(code_to_compile, {}, local_env)
    except Exception as e:
        write_result(val_file, "FAIL", [f"Failed to execute code: {e}"], validator_version)
        return

    GeneratedClass = local_env.get("GeneratedDummy")
    method_name = spec.get("method", "grow") if spec else "grow"
    if not GeneratedClass or not hasattr(GeneratedClass, method_name):
        write_result(val_file, "FAIL", [f"No {method_name} method found in generated class."], validator_version)
        return

    if is_contract:
        run_invariant_validation(GeneratedClass, clean_code, val_file, spec)
    else:
        run_legacy_validation(GeneratedClass, clean_code, val_file)

def run_legacy_validation(GeneratedClass, clean_code, val_file):
    notes = []
    passed_all = True
    
    if "random.choice" in clean_code:
        notes.append("Failed: random.choice still hardcoded.")
        passed_all = False
        
    if "self.generate_reward()" not in clean_code and "self._generate_reward()" not in clean_code:
        notes.append("Failed: self.generate_reward() not called in text.")
        passed_all = False

    class TestEnv(GeneratedClass):
        def __init__(self, reward_value):
            self.reward_value = reward_value
            self.strategy_scores = {1: 0.5, 2: 0.5}
            self.memory = []
            self.generate_reward_called = False
            
        def choose_action(self):
            return 1
            
        def generate_reward(self):
            self.generate_reward_called = True
            return self.reward_value
            
        def _generate_reward(self):
            self.generate_reward_called = True
            return self.reward_value

    try:
        test1 = TestEnv(1)
        old_score1 = test1.strategy_scores[1]
        test1.grow()
        
        if not test1.generate_reward_called:
            notes.append("Failed: generate_reward was not executed.")
            passed_all = False
            
        new_score1 = test1.strategy_scores[1]
        expected1 = old_score1 + 1
        if new_score1 != expected1:
            notes.append(f"Failed: chosen action score did not correctly increase (expected {expected1}, got {new_score1}).")
            passed_all = False
            
        if test1.strategy_scores[2] != 0.5:
            notes.append("Failed: non-chosen action score updated.")
            passed_all = False
            
        if not test1.memory:
            notes.append("Failed: memory not appended.")
            passed_all = False
        else:
            mem = test1.memory[0]
            if not all(k in mem for k in ["action", "reward", "old_score", "delta", "new_score"]):
                notes.append("Failed: memory missing required keys.")
                passed_all = False
                
        test2 = TestEnv(-1)
        old_score2 = test2.strategy_scores[1]
        test2.grow()
        new_score2 = test2.strategy_scores[1]
        expected2 = old_score2 - 1
        if new_score2 != expected2:
            notes.append(f"Failed: reward swap did not correctly decrease the score (expected {expected2}, got {new_score2}).")
            passed_all = False

    except Exception as e:
        notes.append(f"Failed during execution: {e}")
        passed_all = False
        
    if passed_all:
        write_result(val_file, "PASS", ["All behavioral tests passed."], "2.0.0")
    else:
        write_result(val_file, "FAIL", notes, "2.0.0")

def check_delta(env, old_scores, mem_before, r, s, a):
    new_score = env.strategy_scores[a]
    expected_score = old_scores[a] + r
    if new_score != expected_score:
        return f"Failed Delta Invariant [r={r}, s={s}, a={a}]: {new_score} != {expected_score}"
    return None

def check_isolation(env, old_scores, mem_before, r, s, a):
    changed_keys = [k for k, v in env.strategy_scores.items() if v != old_scores[k]]
    if r != 0:
        if len(changed_keys) != 1 or changed_keys[0] != a:
            return f"Failed Isolation Invariant [r={r}, s={s}, a={a}]: Changed keys {changed_keys}, expected [{a}]"
    else:
        if len(changed_keys) != 0:
            return f"Failed Isolation Invariant [r={r}, s={s}, a={a}]: Changed keys {changed_keys}, expected [] since r=0"
    return None

def check_memory_growth(env, old_scores, mem_before, r, s, a):
    mem_after = len(env.memory)
    if mem_after != mem_before + 1:
        return f"Failed Memory Growth Invariant [r={r}, s={s}, a={a}]: {mem_after} != {mem_before} + 1"
    return None

def check_memory_coherence(env, old_scores, mem_before, r, s, a):
    mem_after = len(env.memory)
    if mem_after <= mem_before:
        return f"Failed Memory Coherence [r={r}, s={s}, a={a}]: Memory did not grow"
    last_mem = env.memory[-1]
    if not isinstance(last_mem, dict):
        return f"Failed Memory Coherence [r={r}, s={s}, a={a}]: memory item is not a dict"
    if last_mem.get("new_score") != env.strategy_scores[a]:
        return f"Failed Memory Coherence [r={r}, s={s}, a={a}]: new_score mismatch"
    if last_mem.get("old_score") != old_scores[a]:
        return f"Failed Memory Coherence [r={r}, s={s}, a={a}]: old_score mismatch"
    if last_mem.get("reward") != r:
        return f"Failed Memory Coherence [r={r}, s={s}, a={a}]: reward mismatch"
    if last_mem.get("delta") != r:
        return f"Failed Memory Coherence [r={r}, s={s}, a={a}]: delta mismatch"
    return None

INVARIANT_REGISTRY = {
    "delta": check_delta,
    "isolation": check_isolation,
    "memory_growth": check_memory_growth,
    "memory_coherence": check_memory_coherence
}

def run_invariant_validation(GeneratedClass, clean_code, val_file, spec):
    notes = []
    passed_all = True
    
    if "random.choice" in clean_code:
        notes.append("Failed: random.choice still hardcoded.")
        passed_all = False
        
    class TestEnv(GeneratedClass):
        def __init__(self, reward_value, init_score, chosen_action):
            self.reward_value = reward_value
            self.strategy_scores = {1: init_score, 2: init_score}
            self.memory = []
            self.generate_reward_called = False
            self.chosen_action = chosen_action
            
        def choose_action(self):
            return self.chosen_action
            
        def generate_reward(self):
            self.generate_reward_called = True
            return self.reward_value
            
        def _generate_reward(self):
            self.generate_reward_called = True
            return self.reward_value

    rewards = [-3, -1, 0, 1, 2.5]
    initial_scores = [0, 0.5, 10, -4]
    actions = [1, 2]
    
    # Get invariants from spec, or default to all if not specified (for RL_008 backwards compatibility)
    invariants_to_test = spec.get("invariants", [])
    if not invariants_to_test:
        invariants_to_test = [
            {"type": "delta"},
            {"type": "isolation"},
            {"type": "memory_growth"},
            {"type": "memory_coherence"}
        ]
        
    active_invariants = []
    for inv in invariants_to_test:
        inv_type = inv.get("type")
        if inv_type in INVARIANT_REGISTRY:
            active_invariants.append(INVARIANT_REGISTRY[inv_type])
        else:
            notes.append(f"Warning: Unknown invariant type '{inv_type}' requested in contract.")
            passed_all = False
            
    try:
        method_name = spec.get("method", "grow") if spec else "grow"
        for r in rewards:
            for s in initial_scores:
                for a in actions:
                    env = TestEnv(r, s, a)
                    old_scores = dict(env.strategy_scores)
                    mem_before = len(env.memory)
                    
                    method_to_call = getattr(env, method_name, None)
                    if not method_to_call:
                        notes.append(f"No {method_name} method found in generated class.")
                        passed_all = False
                        break
                        
                    method_to_call()
                    
                    if not env.generate_reward_called:
                        notes.append(f"Failed [r={r}, s={s}, a={a}]: generate_reward was not executed.")
                        passed_all = False
                        
                    for inv_func in active_invariants:
                        err = inv_func(env, old_scores, mem_before, r, s, a)
                        if err:
                            notes.append(err)
                            passed_all = False
                                
    except Exception as e:
        notes.append(f"Failed during execution: {e}")
        passed_all = False
        
    if passed_all:
        write_result(val_file, "PASS", ["All parameterized invariant tests passed."], "3.0.0")
    else:
        # Deduplicate notes to avoid massive output
        dedup_notes = list(dict.fromkeys(notes))
        if len(dedup_notes) > 10:
            dedup_notes = dedup_notes[:10] + [f"...and {len(dedup_notes)-10} more errors."]
        write_result(val_file, "FAIL", dedup_notes, "3.0.0")

def write_result(path, status, notes, version):
    res = {
        "validator_version": version,
        "validation_status": status,
        "notes": notes
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=4)
    print(f"Validation saved to {path} with status {status}")
    print(json.dumps(res, indent=4))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run parameterized invariant behavioral validation.")
    parser.add_argument("experiment_id", help="The ID of the experiment")
    parser.add_argument("--dir", default=r"D:\Mind\Laboratory\Experiments", help="Base directory")
    parser.add_argument("--attempt", type=int, default=1, help="The attempt number")
    args = parser.parse_args()
    
    run_validation(args.experiment_id, args.dir, attempt=args.attempt)
