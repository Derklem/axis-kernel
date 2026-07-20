import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

def main():
    base_dir = Path(__file__).resolve().parent.parent
    inputs_dir = base_dir / "inputs"
    obs_dir = base_dir / "observation"
    state_dir = base_dir / "state"

    for d in [obs_dir, state_dir]:
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    env_python = str(base_dir.parent / "env" / "Scripts" / "python.exe")

    # 1. Setup mock run directory
    run_dir = inputs_dir / "RUN_MALFORMED"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Write a valid receipt
    receipt = {
        "run_id": "RUN_MALFORMED",
        "evaluation": {
            "overall_result": True
        },
        "artifacts": {
            "evaluation.json": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        }
    }
    with open(run_dir / "receipt.json", "w") as f: json.dump(receipt, f, indent=2)

    # Setup base arguments for observation.cli
    obs_args = [
        env_python, "-m", "observation.cli",
        "--receipt", str(run_dir / "receipt.json"),
        "--artifact-path", "evaluation.json",
        "--artifact", str(run_dir / "evaluation.json"),
        "--verification-artifact", str(run_dir / "verification.json")
    ]

    # Write a dummy verification artifact
    with open(run_dir / "verification.json", "w") as f:
        json.dump({"verified": True}, f)

    # Test A: Missing fields
    print("Test A: Missing required fields...")
    with open(run_dir / "evaluation.json", "w") as f:
        json.dump({"outcome": "SUPPORTED"}, f) # missing observed, expected, metric
    
    out_a = obs_dir / "feed_a.json"
    res = subprocess.run(obs_args + ["--output", str(out_a)], capture_output=True, text=True)
    assert res.returncode == 1
    assert "Extraction failed" in res.stderr
    print("Test A Passed: Extractor gracefully aborted via hard error.")

    # Test B: Incorrect types
    print("Test B: Incorrect types...")
    with open(run_dir / "evaluation.json", "w") as f:
        json.dump({
            "outcome": "SUPPORTED",
            "metric": "test",
            "observed": "1", # string instead of number
            "expected": 1
        }, f)
        
    out_b = obs_dir / "feed_b.json"
    res = subprocess.run(obs_args + ["--output", str(out_b)], capture_output=True, text=True)
    assert res.returncode == 1
    assert "Extraction failed" in res.stderr
    print("Test B Passed: Extractor gracefully aborted via hard error.")
    
    # Test C: Invalid JSON
    print("Test C: Invalid JSON syntax...")
    with open(run_dir / "evaluation.json", "w") as f:
        f.write("{ invalid json")
        
    out_c = obs_dir / "feed_c.json"
    res = subprocess.run(obs_args + ["--output", str(out_c)], capture_output=True, text=True)
    assert res.returncode == 1
    print("Test C Passed: Extractor gracefully aborted via JSON decoding error.")

if __name__ == "__main__":
    main()
