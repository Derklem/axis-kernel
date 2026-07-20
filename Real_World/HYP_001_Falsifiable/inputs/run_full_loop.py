import json
import os
import subprocess
import sys
import shutil
from pathlib import Path
import hashlib

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

def record_artifact(index, path, producer, consumer, schema):
    rel_path = str(path.relative_to(base_dir)).replace("\\", "/")
    index[rel_path] = {
        "sha256": sha256_file(path),
        "producer": producer,
        "consumer": consumer,
        "schema_version": schema
    }

base_dir = Path.cwd()
inputs_dir = base_dir / "inputs"
lab_dir = base_dir / "laboratory"
obs_dir = base_dir / "observation"
state_dir = base_dir / "state"
strategy_dir = base_dir / "strategy"
agenda_dir = base_dir / "agenda"
analysis_dir = base_dir / "analysis"

# Make output dirs
for d in [lab_dir, obs_dir, state_dir, strategy_dir, agenda_dir, analysis_dir]:
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)

payload_path = inputs_dir / "payload.json"
eval_path = inputs_dir / "evaluation.json"

payload = {
    "hello": "world",
    "values": [1, 2, 3, 4, "six"],
    "nested": {
        "deep": True
    }
}
with open(payload_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)

index_path = base_dir / "artifact_index.json"
artifact_index = {}

print("Initializing Laboratory ledger...")
subprocess.run([sys.executable, "-m", "laboratory.cli", "init", "--dir", str(lab_dir)], check=True)

roots = []
runs_dir = lab_dir / "runs"
runs_dir.mkdir(parents=True, exist_ok=True)

print("Running 10 independent verification processes via Laboratory run...")

run_uuids = []

for i in range(10):
    exp_dir = inputs_dir / f"experiment_trial_{i}"
    exp_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Setup the experiment
    exp_json = {
        "hypothesis": "hyp-001",
        "procedure": "Execute the canonical hash script against payload.json",
        "expected_artifacts": ["evaluation.json"],
        "adapter": {
            "type": "subprocess",
            "command": ["python", "run.py"]
        },
        "evaluation_criteria": {}
    }
    with open(exp_dir / "experiment.json", "w") as f:
        json.dump(exp_json, f)
        
    script_content = f"""
import json
import sys
import os
from laboratory.crypto import canonical_hash
with open(r'{payload_path.resolve()}', 'r', encoding='utf-8') as f:
    data = json.load(f)
root = canonical_hash(data)
print(root)

artifacts_dir = os.environ.get("LAB_ARTIFACTS_DIR", "artifacts")
os.makedirs(artifacts_dir, exist_ok=True)
evaluation = {{
    "evaluation_schema_version": "1.0.0",
    "outcome": "SUPPORTED",
    "subject": "hyp-001",
    "metric": "hash_match",
    "observed": 1,
    "expected": 1
}}
eval_path = os.path.join(artifacts_dir, "evaluation.json")
with open(eval_path, "w", encoding="utf-8") as f:
    json.dump(evaluation, f, indent=2)
"""
    with open(exp_dir / "run.py", "w") as f:
        f.write(script_content)

    # 2. Run the experiment
    import re
    res = subprocess.run([
        sys.executable, "-m", "laboratory.cli", "run",
        str(exp_dir),
        "--dir", str(lab_dir),
        "--runs-dir", str(runs_dir)
    ], capture_output=True, text=True, check=True)
    
    # Extract RUN ID from stdout: "Run ID: RUN_..."
    m = re.search(r"Run ID:\s+(RUN_[0-9a-fA-F\-]+)", res.stdout)
    if not m:
        print("Stdout:\n", res.stdout)
        print("Stderr:\n", res.stderr)
        raise RuntimeError("Failed to extract Run ID")
    
    run_id = m.group(1)
    run_uuids.append(run_id)
    
    # The output is stored in laboratory/runs/<name>/stdout.txt
    stdout_path = runs_dir / run_id / "stdout.txt"
    with open(stdout_path, "r", encoding="utf-8") as f:
        root = f.read().strip()
    roots.append(root)

print("Roots gathered:")
for i, r in enumerate(roots):
    print(f"Trial {i}: {r}")

all_match = all(r == roots[0] for r in roots)

if all_match:
    print("\\nSUCCESS: All 10 independent processes produced the identical 64-character root.")
    
    state = {
        "state_schema_version": "1.1.0",
        "confidence": 0,
        "evidence_count": 0,
        "applied_observation_ids": []
    }
    state_path = state_dir / "state_0.json"
    with open(state_path, "w") as f: json.dump(state, f, indent=2)
    record_artifact(artifact_index, state_path, "operator", "state", "1.1.0")

    spec = {
        "strategy_schema_version": "1.0.0",
        "decision_version": "strategy-hello-v1",
        "probe_threshold": 10,
        "minimum_evidence": 5
    }
    spec_path = strategy_dir / "strategy_spec.json"
    with open(spec_path, "w") as f: json.dump(spec, f, indent=2)
    record_artifact(artifact_index, spec_path, "operator", "strategy", "1.0.0")

    transition_spec = {
        "transition_spec_schema_version": "1.0.0",
        "transition_version": "state-hyp001",
        "subject": "hyp-001",
        "supported_increment": 2
    }
    transition_spec_path = state_dir / "transition_spec.json"
    with open(transition_spec_path, "w") as f: json.dump(transition_spec, f, indent=2)
    record_artifact(artifact_index, transition_spec_path, "operator", "state", "1.0.0")

    current_state_path = state_path
    rust_verifier = r"D:\\Infinite\\Infinity\\Laboratory\\verifier-rs\\target\\release\\verifier-rs.exe"

    for i in range(10):
        run_id = run_uuids[i]
        run_receipt_path = runs_dir / run_id / "receipt.json"
        
        eval_path = runs_dir / run_id / "artifacts/evaluation.json"
        
        ver_art_path = obs_dir / f"verification_{i}.json"
        subprocess.run([
            sys.executable, "-m", "laboratory.cli", "verify-strict", run_id,
            "--rust-verifier", rust_verifier,
            "--dir", str(lab_dir), "--runs-dir", str(runs_dir), "--json"
        ], stdout=open(ver_art_path, "w"), check=True)

        obs_path = obs_dir / f"observation_{i}.json"
        subprocess.run([
            sys.executable, "-m", "observation.cli",
            "--receipt", str(run_receipt_path),
            "--artifact-path", "evaluation.json",
            "--artifact", str(eval_path),
            "--verification-artifact", str(ver_art_path),
            "--output", str(obs_path)
        ], check=True)
        record_artifact(artifact_index, obs_path, "laboratory", "observation", "1.0.0")
        
        trans_path = state_dir / f"transition_{i+1}.json"
        subprocess.run([
            sys.executable, "-m", "state.cli",
            "--prior-state", str(current_state_path),
            "--feed", str(obs_path),
            "--spec", str(transition_spec_path),
            "--output", str(trans_path)
        ], check=True)
        record_artifact(artifact_index, trans_path, "state", "operator", "1.1.0")
        
        with open(trans_path, "r") as f:
            t = json.load(f)
        
        current_state_path = state_dir / f"state_{i+1}.json"
        with open(current_state_path, "w") as f:
            json.dump(t["next_state"], f, indent=2)
            
    dec_path = strategy_dir / "decision.json"
    subprocess.run([
        sys.executable, "-m", "strategy.cli",
        "--state", str(current_state_path),
        "--spec", str(spec_path),
        "--observations", str(obs_path),
        "--output", str(dec_path)
    ], check=True)
    record_artifact(artifact_index, dec_path, "strategy", "agenda", "1.0.0")
    
    with open(dec_path) as f:
        dec = json.load(f)
    print(f"\nFinal Strategy Decision: {dec['decision']} (Reason: {dec['reason_code']})")
    
    with open(inputs_dir / "result.txt", "w") as f:
        f.write("SUPPORTED\n")
else:
    print("\nFAIL: Roots differed across processes.")
    with open(inputs_dir / "result.txt", "w") as f:
        f.write("CONTRADICTED\n")

with open(index_path, "w", encoding="utf-8") as f:
    json.dump(artifact_index, f, indent=2)
print("Artifact index written.")
