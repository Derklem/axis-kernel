import os
import subprocess

def modify_and_diff(filepath, new_content, diff_name):
    # Ensure physical original exists
    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    try:
        diff_output = subprocess.check_output(["git", "diff", "--no-index", "-", filepath], input=original.encode("utf-8")).decode("utf-8")
    except subprocess.CalledProcessError as e:
        diff_output = e.output.decode("utf-8")
        
    fixed_diff = []
    for line in diff_output.splitlines():
        if line.startswith("--- a/-"):
            fixed_diff.append(f"--- a/{filepath}")
        elif line.startswith("+++ b/"):
            fixed_diff.append(f"+++ b/{filepath}")
        else:
            fixed_diff.append(line)
            
    with open(diff_name, "w", encoding="utf-8") as f:
        f.write("\n".join(fixed_diff))
        
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(original)

# Case I: Trivial hygiene in non-validator
with open("hygiene_pass.py", "r", encoding="utf-8") as f: txt = f.read()
modify_and_diff("hygiene_pass.py", txt + "\n# Simple comment\n", "case_I.diff")

# Case J: Feature addition in non-validator (Lots of lines)
new_lines = "\n".join([f"# Feature line {i}" for i in range(25)])
modify_and_diff("hygiene_pass.py", txt + "\n" + new_lines + "\n", "case_J.diff")

# Case K: Real refactor in strategy_engine.py (Validator!)
# Wait, strategy_engine.py is a validator. Any edit will have semantic risk checked. If score == 0, it passes.
with open("strategy_engine.py", "r", encoding="utf-8") as f: strat = f.read()
modify_and_diff("strategy_engine.py", strat + "\n# Just a docstring update\n", "case_K.diff")

# Case L: Edge case that barely passes semantic risk (Score 1.0, but not validator)
modify_and_diff("hygiene_pass.py", txt + "\n# RECEPTOR_CHAIN_COMMITTED_TO_MAIN_LEDGER\nif False:\n    pass\n", "case_L.diff")

print("Generated 4 Phase 199 test diffs.")