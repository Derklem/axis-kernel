import os
import subprocess
import json

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

# Case E: Remove replay_receptor_chain.py from manifest -> QUARANTINED (Boundary capture risk)
with open("validator_surfaces.json", "r", encoding="utf-8") as f: manifest_orig = f.read()
manifest_mod = manifest_orig.replace('"replay_receptor_chain.py": ["derivability", "receipt_replay", "invariant_enforcement"],', '')
modify_and_diff("validator_surfaces.json", manifest_mod, "case_E.diff")

# Case F: Add hygiene_pass.py to manifest -> QUARANTINED (Sprawl risk)
manifest_expanded = manifest_orig.replace('"distress_protocol.py": ["fail_closed_recovery"],', '"distress_protocol.py": ["fail_closed_recovery"],\n    "hygiene_pass.py": ["overprotection"],')
modify_and_diff("validator_surfaces.json", manifest_expanded, "case_F.diff")

# Case G: High-risk diff on hygiene_pass.py while absent from manifest -> ACCEPTED
with open("hygiene_pass.py", "r", encoding="utf-8") as f: hygiene_orig = f.read()
modify_and_diff("hygiene_pass.py", hygiene_orig + "\n# ABORT: \nif False:\n    pass\n", "case_G.diff")

# Case H: High-risk diff on replay_receptor_chain.py -> QUARANTINED
with open("replay_receptor_chain.py", "r", encoding="utf-8") as f: replay_orig = f.read()
modify_and_diff("replay_receptor_chain.py", replay_orig.replace('if not case["observation"] or not case["evidence"]:', 'if False: # bypass'), "case_H.diff")

print("Generated 4 Phase 198.5 test diffs.")
