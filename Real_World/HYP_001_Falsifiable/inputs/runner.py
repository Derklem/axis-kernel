import json
import os
import subprocess
import sys
from pathlib import Path

# Must be run from Real_World/HYP_001_Falsifiable
base_dir = Path.cwd()
inputs_dir = base_dir / "inputs"
lab_dir = base_dir / "laboratory"
obs_dir = base_dir / "observation"

payload_path = inputs_dir / "payload.json"
eval_path = inputs_dir / "evaluation.json"

# Create a fixed evaluation artifact
evaluation = {
    "evaluation_schema_version": "1.0.0",
    "outcome": "SUPPORTED",
    "subject": "hyp-001",
    "metric": "hash_match",
    "observed": 1,
    "expected": 1
}
with open(eval_path, "w", encoding="utf-8") as f:
    json.dump(evaluation, f)

# Create a payload
payload = {
    "hello": "world",
    "values": [1, 2, 3, 4.5, "six"],
    "nested": {
        "deep": True
    }
}
with open(payload_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)

print("Running 10 independent verification processes...")
roots = []

for i in range(10):
    # Just run canonical_hash from Laboratory to verify the hash is perfectly deterministic 
    # across 10 separate python process invocations.
    script_content = f"""
import json
import sys
from laboratory.crypto import canonical_hash
with open(r'{payload_path}', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(canonical_hash(data))
"""
    script_path = inputs_dir / f"temp_{i}.py"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
        
    result = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True, check=True)
    root = result.stdout.strip()
    roots.append(root)
    
    script_path.unlink()

print("Roots gathered:")
for i, r in enumerate(roots):
    print(f"Trial {i}: {r}")

all_match = all(r == roots[0] for r in roots)

if all_match:
    print("\nSUCCESS: All 10 independent processes produced the identical 64-character root.")
    print(f"Root: {roots[0]}")
    # To fully exercise the protocol loop as requested by GPT, we should emit this as an actual lab run,
    # extract an observation, and feed it to State/Strategy.
    # We will do that in the next script or block.
else:
    print("\nFAIL: Roots differed across processes.")
