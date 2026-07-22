import json
import os
import shutil
import subprocess
from pathlib import Path

def main():
    base_dir = Path("proof")
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir()
    
    ledger_dir = base_dir / "ledger"
    ledger_dir.mkdir()
    
    runs_dir = base_dir / "runs"
    runs_dir.mkdir()
    
    # Initialize ledger
    subprocess.run(["python", "-m", "laboratory.cli", "init", "--dir", str(ledger_dir)], check=True)
    
    exp_dir = base_dir / "experiment"
    exp_dir.mkdir()
    
    inputs_dir = exp_dir / "inputs"
    inputs_dir.mkdir()
    
    # Create the three Strategy JSON documents
    state = {
        "state_schema_version": "1.0.0",
        "confidence": 95,
        "evidence_count": 100
    }
    with open(inputs_dir / "state.json", "w") as f:
        json.dump(state, f, indent=2)
        
    spec = {
        "strategy_schema_version": "1.0.0",
        "decision_version": "strategy-hello-v1",
        "probe_threshold": 90,
        "minimum_evidence": 50
    }
    with open(inputs_dir / "strategy_spec.json", "w") as f:
        json.dump(spec, f, indent=2)
        
    observations = [{"support": 1}]
    with open(inputs_dir / "observations.json", "w") as f:
        json.dump(observations, f, indent=2)
        
    # Create experiment spec
    exp = {
        "hypothesis": "Strategy Evaluator produces deterministic decision artifact",
        "procedure": "Execute purely functional evaluate()",
        "adapter": {
            "type": "subprocess",
            "command": [
                "python", "-m", "strategy.cli",
                "--state", "inputs/state.json",
                "--spec", "inputs/strategy_spec.json",
                "--observations", "inputs/observations.json",
                "--output", "artifacts/decision.json"
            ]
        },
        "evaluation_criteria": {
            "deterministic_checks": [
                {
                    "name": "exit_code_equals",
                    "expected_exit_code": 0
                }
            ]
        }
    }
    with open(exp_dir / "experiment.json", "w") as f:
        json.dump(exp, f, indent=2)
        
    print("Running Laboratory Experiment...")
    res = subprocess.run([
        "python", "-m", "laboratory.cli", "run", str(exp_dir),
        "--dir", str(ledger_dir),
        "--runs-dir", str(runs_dir)
    ], capture_output=True, text=True)
    
    if res.returncode != 0:
        print("Experiment run failed!")
        print(res.stderr)
        return
        
    # Extract run ID
    import re
    m = re.search(r"Run ID:\s+(RUN_[a-f0-9\-]+)", res.stdout)
    if not m:
        print("Could not parse RUN ID from output!")
        print(res.stdout)
        return
    run_id = m.group(1)
    print(f"Executed Run ID: {run_id}")
    
    print("\nVerifying with Python Verifier...")
    py_res = subprocess.run([
        "python", "-m", "laboratory.cli", "verify", run_id,
        "--dir", str(ledger_dir),
        "--runs-dir", str(runs_dir)
    ], capture_output=True, text=True)
    print(py_res.stdout)
    
    print("\nVerifying with Rust Verifier...")
    rs_verifier = Path("../Laboratory/verifier-rs/target/debug/verifier-rs.exe")
    rs_res = subprocess.run([
        str(rs_verifier),
        run_id,
        "--ledger-dir", str(ledger_dir),
        "--runs-dir", str(runs_dir)
    ], capture_output=True, text=True)
    if rs_res.stdout:
        print("STDOUT:")
        print(rs_res.stdout)
    if rs_res.stderr:
        print("STDERR:")
        print(rs_res.stderr)
    
if __name__ == "__main__":
    main()
