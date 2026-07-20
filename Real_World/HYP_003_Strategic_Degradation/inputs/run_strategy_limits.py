import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

def run_strategy(state, spec, obs, out_path, env_python):
    base_dir = Path(__file__).resolve().parent.parent
    inputs_dir = base_dir / "inputs"
    
    state_path = inputs_dir / "temp_state.json"
    spec_path = inputs_dir / "temp_spec.json"
    obs_path = inputs_dir / "temp_obs.json"
    
    with open(state_path, "w") as f: json.dump(state, f, indent=2)
    with open(spec_path, "w") as f: json.dump(spec, f, indent=2)
    with open(obs_path, "w") as f: json.dump(obs, f, indent=2)
    
    subprocess.run([
        env_python, "-m", "strategy.cli",
        "--state", str(state_path),
        "--spec", str(spec_path),
        "--observations", str(obs_path),
        "--output", str(out_path)
    ], check=True)
    
    with open(out_path, "r") as f:
        return json.load(f)

def main():
    base_dir = Path(__file__).resolve().parent.parent
    strategy_dir = base_dir / "strategy"
    if strategy_dir.exists():
        shutil.rmtree(strategy_dir)
    strategy_dir.mkdir(parents=True, exist_ok=True)
    
    env_python = str(base_dir.parent / "env" / "Scripts" / "python.exe")
    
    spec = {
        "strategy_schema_version": "1.0.0",
        "decision_version": "strategy-hello-v1",
        "probe_threshold": 50,
        "minimum_evidence": 100
    }
    
    # Mock observation feed object (for --observations arg)
    obs = {
        "observation_schema_version": "1.0.0",
        "kind": "feed",
        "observations": []
    }
    
    # Test 1: Confidence below probe threshold
    # Expect: PROBE (Reason: INSUFFICIENT_CONFIDENCE)
    state_1 = {
        "state_schema_version": "1.1.0",
        "confidence": 49,
        "evidence_count": 200,
        "applied_observation_ids": []
    }
    res_1 = run_strategy(state_1, spec, obs, strategy_dir / "decision_1.json", env_python)
    assert res_1["decision"] == "PROBE"
    assert res_1["reason_code"] == "INSUFFICIENT_CONFIDENCE"
    print("Test 1 Passed: PROBE when confidence (49) < threshold (50)")

    # Test 2: Confidence equal to probe threshold, evidence below min
    # Expect: PROBE (Reason: INSUFFICIENT_EVIDENCE)
    state_2 = {
        "state_schema_version": "1.1.0",
        "confidence": 50,
        "evidence_count": 99,
        "applied_observation_ids": []
    }
    res_2 = run_strategy(state_2, spec, obs, strategy_dir / "decision_2.json", env_python)
    assert res_2["decision"] == "PROBE"
    assert res_2["reason_code"] == "INSUFFICIENT_EVIDENCE"
    print("Test 2 Passed: PROBE when confidence (50) >= threshold (50) but evidence (99) < min (100)")

    # Test 3: Both thresholds met exactly
    # Expect: HOLD (Reason: THRESHOLDS_SATISFIED)
    state_3 = {
        "state_schema_version": "1.1.0",
        "confidence": 50,
        "evidence_count": 100,
        "applied_observation_ids": []
    }
    res_3 = run_strategy(state_3, spec, obs, strategy_dir / "decision_3.json", env_python)
    assert res_3["decision"] == "HOLD"
    assert res_3["reason_code"] == "THRESHOLDS_SATISFIED"
    print("Test 3 Passed: HOLD when thresholds are exactly met")

    # Test 4: Both thresholds exceeded
    # Expect: HOLD (Reason: THRESHOLDS_SATISFIED)
    state_4 = {
        "state_schema_version": "1.1.0",
        "confidence": 99,
        "evidence_count": 5000,
        "applied_observation_ids": []
    }
    res_4 = run_strategy(state_4, spec, obs, strategy_dir / "decision_4.json", env_python)
    assert res_4["decision"] == "HOLD"
    assert res_4["reason_code"] == "THRESHOLDS_SATISFIED"
    print("Test 4 Passed: HOLD when thresholds are exceeded")
    
    print("All strategy logic limits evaluated deterministically successfully!")

if __name__ == "__main__":
    main()
