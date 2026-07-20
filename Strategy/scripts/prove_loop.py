import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from laboratory.crypto import canonical_hash

def main():
    base_dir = Path("proof_loop")
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir()
    
    ledger_dir = base_dir / "ledger"
    ledger_dir.mkdir()
    runs_dir = base_dir / "runs"
    runs_dir.mkdir()
    
    subprocess.run(["python", "-m", "laboratory.cli", "init", "--dir", str(ledger_dir)], check=True)
    
    print("--- 1. Initial Strategy Decision ---")
    inputs1_dir = base_dir / "strategy_inputs_1"
    inputs1_dir.mkdir()
    
    state = {
        "state_schema_version": "1.1.0",
        "confidence": 95,
        "evidence_count": 40,
        "applied_observation_ids": []
    }
    with open(inputs1_dir / "state.json", "w") as f: json.dump(state, f, indent=2)
    spec = {
        "strategy_schema_version": "1.0.0",
        "decision_version": "strategy-hello-v1",
        "probe_threshold": 90,
        "minimum_evidence": 50
    }
    with open(inputs1_dir / "strategy_spec.json", "w") as f: json.dump(spec, f, indent=2)
    obs = {
        "observation_schema_version": "1.0.0",
        "observations": []
    }
    with open(inputs1_dir / "observations.json", "w") as f: json.dump(obs, f, indent=2)
    
    dec1_path = base_dir / "decision_1.json"
    subprocess.run([
        "python", "-m", "strategy.cli",
        "--state", str(inputs1_dir / "state.json"),
        "--spec", str(inputs1_dir / "strategy_spec.json"),
        "--observations", str(inputs1_dir / "observations.json"),
        "--output", str(dec1_path)
    ], check=True)
    
    with open(dec1_path) as f:
        dec1 = json.load(f)
    print(f"Decision 1: {dec1['decision']} ({dec1['reason_code']})")
    print(f"Input Root 1: {dec1['input_root']}")
    
    print("\n--- 2. Laboratory Experiment ---")
    exp_dir = base_dir / "experiment"
    exp_dir.mkdir()
    exp_inputs = exp_dir / "inputs"
    exp_inputs.mkdir()
    exp_artifacts = exp_dir / "artifacts"
    exp_artifacts.mkdir()
    
    shutil.copy(dec1_path, exp_inputs / "decision.json")
    
    eval_art = {
        "evaluation_schema_version": "1.0.0",
        "outcome": "SUPPORTED",
        "subject": "strategy-hello-v1",
        "metric": "decision_reproduced",
        "observed": 1,
        "expected": 1
    }
    with open(exp_dir / "emit.py", "w") as f:
        f.write(f'''
import json
import os
import pathlib
artifacts_dir = pathlib.Path(os.environ["LAB_ARTIFACTS_DIR"])
with open(artifacts_dir / "evaluation.json", "w") as out:
    json.dump({json.dumps(eval_art)}, out)
''')
    
    exp = {
        "hypothesis": "Test observation extraction loop",
        "procedure": "Emit an evaluation artifact",
        "expected_artifacts": [
            "evaluation.json"
        ],
        "adapter": {
            "type": "subprocess",
            "command": ["python", "emit.py"]
        },
        "evaluation_criteria": {
            "deterministic_checks": [
                {"name": "exit_code_equals", "expected_exit_code": 0}
            ]
        }
    }
    with open(exp_dir / "experiment.json", "w") as f: json.dump(exp, f, indent=2)
    
    res = subprocess.run([
        "python", "-m", "laboratory.cli", "run", str(exp_dir),
        "--dir", str(ledger_dir),
        "--runs-dir", str(runs_dir)
    ], capture_output=True, text=True, check=True)
    
    import re
    m = re.search(r"Run ID:\s+(RUN_[a-f0-9\-]+)", res.stdout)
    run_id = m.group(1)
    print(f"Laboratory Run ID: {run_id}")
    
    print("\n--- 3. Observation Extraction ---")
    run_receipt_path = runs_dir / run_id / "receipt.json"
    run_eval_path = runs_dir / run_id / "artifacts" / "evaluation.json"
    
    # Compile Rust verifier
    print("Compiling Rust Verifier...")
    rust_project_dir = Path("D:/Infinite/Infinity/Laboratory/verifier-rs")
    cargo_path = Path.home() / ".cargo" / "bin" / "cargo.exe"
    if not cargo_path.exists():
        cargo_path = "cargo" # fallback
    subprocess.run(
        f'"{cargo_path}" build --manifest-path "{rust_project_dir / "Cargo.toml"}" --release', 
        shell=True, check=True
    )
    rust_verifier_bin = rust_project_dir / "target" / "release" / "verifier-rs.exe"
    
    # Strict Verification
    print("Running Strict Verification...")
    ver_art_path = base_dir / "verification.json"
    subprocess.run([
        "python", "-m", "laboratory.cli", "verify-strict", run_id,
        "--rust-verifier", str(rust_verifier_bin),
        "--dir", str(ledger_dir),
        "--runs-dir", str(runs_dir),
        "--json"
    ], stdout=open(ver_art_path, "w"), check=True)
    
    with open(ver_art_path) as f:
        ver_art = json.load(f)
    print(f"Verification: Python={ver_art['python_verifier']['result']}, Rust={ver_art['rust_verifier']['result']}")
    
    obs_path = base_dir / "new_observations.json"
    subprocess.run([
        "python", "-m", "observation.cli",
        "--receipt", str(run_receipt_path),
        "--artifact-path", "evaluation.json",
        "--artifact", str(run_eval_path),
        "--verification-artifact", str(ver_art_path),
        "--output", str(obs_path)
    ], check=True)
    
    with open(obs_path) as f:
        new_obs = json.load(f)
    print(f"Extracted Observation Support: {new_obs['observations'][0]['support']}")
    
    
    # ==========================================
    # 4. State Engine Transition 1
    # ==========================================
    transition_spec_path = runs_dir / "transition_spec.json"
    transition_spec = {
        "transition_spec_schema_version": "1.0.0",
        "transition_version": "state-hello-v1",
        "subject": "strategy-hello-v1",
        "supported_increment": 10
    }
    with open(transition_spec_path, "w") as f:
        json.dump(transition_spec, f, indent=2)
        
    transition1_path = runs_dir / "transition1.json"
    print("\n--- 4. State Engine Transition 1 ---")
    subprocess.run([
        sys.executable, "-m", "state.cli",
        "--prior-state", str(inputs1_dir / "state.json"),
        "--feed", str(obs_path),
        "--spec", str(transition_spec_path),
        "--output", str(transition1_path)
    ], check=True)
    
    with open(transition1_path, "r") as f:
        t1 = json.load(f)
    print(f"Evidence Count: {state['evidence_count']} -> {t1['next_state']['evidence_count']}")
    print(f"Observation recorded exactly once: {len(t1['applied_observation_ids']) == 1}")
    print(f"All roots valid: {bool(t1['prior_state_root'] and t1['observation_feed_root'] and t1['transition_spec_root'] and t1['next_state_root'])}")

    # ==========================================
    # 5. State Engine Transition 2 (Replay)
    # ==========================================
    state2_path = runs_dir / "state2.json"
    with open(state2_path, "w") as f:
        json.dump(t1["next_state"], f, indent=2)
        
    transition2_path = runs_dir / "transition2.json"
    print("\n--- 5. State Engine Transition 2 (Replay) ---")
    subprocess.run([
        sys.executable, "-m", "state.cli",
        "--prior-state", str(state2_path),
        "--feed", str(obs_path),
        "--spec", str(transition_spec_path),
        "--output", str(transition2_path)
    ], check=True)

    with open(transition2_path, "r") as f:
        t2 = json.load(f)
    print(f"Next state unchanged: {t1['next_state'] == t2['next_state']}")
    print(f"Observation classified as replayed: {t2['summary']['replayed_skipped'] == 1}")
    print(f"No second increment: {t2['next_state']['evidence_count'] == t1['next_state']['evidence_count']}")

    # ==========================================
    # 6. Second Strategy Decision
    # ==========================================
    print("\n--- 6. Second Strategy Decision ---")
    def evaluate(state, spec, feed):
        out_path = base_dir / "temp_dec.json"
        with open(base_dir / "temp_state.json", "w") as f: json.dump(state, f)
        with open(base_dir / "temp_feed.json", "w") as f: json.dump(feed, f)
        subprocess.run([
            sys.executable, "-m", "strategy.cli",
            "--state", str(base_dir / "temp_state.json"),
            "--spec", str(inputs1_dir / "strategy_spec.json"),
            "--observations", str(base_dir / "temp_feed.json"),
            "--output", str(out_path)
        ], check=True)
        with open(out_path) as f: return json.load(f)

    decision2 = evaluate(t2["next_state"], spec, new_obs)

    print(f"Decision 2: {decision2['decision']} ({decision2['reason_code']})")
    
    env2 = {
        "state": t2["next_state"],
        "strategy_spec": spec,
        "observations": new_obs
    }
    input_root_2 = canonical_hash(env2)
    print(f"Input Root 2: {input_root_2}")

    print("\n--- Summary ---")
    assert decision2["input_root"] == input_root_2
    
    if dec1['input_root'] != input_root_2:
        print("SUCCESS: Input roots differ.")
    if decision2["decision"] == "HOLD":
        print("SUCCESS: Second decision follows the documented rule.")
        assert decision2["reason_code"] == "THRESHOLDS_SATISFIED"
    else:
        print("FAIL: Second decision did not yield HOLD.")

    # ==========================================
    # 7. Negative Verification Tests
    # ==========================================
    print("\n--- 7. Negative Verification Tests ---")
    
    # 7a. Artifact Byte Mismatch
    print("Test 7a: Artifact byte mismatch")
    bad_eval_path = runs_dir / run_id / "artifacts" / "bad_evaluation.json"
    with open(bad_eval_path, "w") as f: json.dump({
        "evaluation_schema_version": "1.0.0",
        "outcome": "SUPPORTED",
        "subject": "strategy-hello-v1",
        "metric": "decision_reproduced_bad",
        "observed": 1,
        "expected": 1
    }, f)
    try:
        subprocess.run([
            "python", "-m", "observation.cli",
            "--receipt", str(run_receipt_path),
            "--artifact-path", "evaluation.json",
            "--artifact", str(bad_eval_path),
            "--verification-artifact", str(ver_art_path),
            "--output", str(obs_path)
        ], capture_output=True, text=True, check=True)
        print("FAIL: Byte mismatch did not raise error.")
    except subprocess.CalledProcessError as e:
        assert "Artifact hash mismatch" in e.stderr
        print("SUCCESS: Byte mismatch rejected.")

    # 7b. Failed Verifier
    print("Test 7b: Failed Verifier")
    bad_ver_art_path = base_dir / "bad_verification.json"
    bad_ver_art = dict(ver_art)
    bad_ver_art["python_verifier"]["result"] = "FAIL"
    with open(bad_ver_art_path, "w") as f: json.dump(bad_ver_art, f)
    try:
        subprocess.run([
            "python", "-m", "observation.cli",
            "--receipt", str(run_receipt_path),
            "--artifact-path", "evaluation.json",
            "--artifact", str(run_eval_path),
            "--verification-artifact", str(bad_ver_art_path),
            "--output", str(obs_path)
        ], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        pass # The extractor currently sys.exits which raises CalledProcessError, but we want to test if it yields UNOBSERVABLE. Wait, the extractor returns a feed with "UNOBSERVABLE", but then it validates against "observation_feed.json". Wait! UNOBSERVABLE isn't a valid support/reason code structure in the feed unless we allow it?
        
    subprocess.run([
        "python", "-m", "observation.cli",
        "--receipt", str(run_receipt_path),
        "--artifact-path", "evaluation.json",
        "--artifact", str(run_eval_path),
        "--verification-artifact", str(bad_ver_art_path),
        "--output", str(obs_path)
    ], check=True) # It should succeed but output UNOBSERVABLE
    
    with open(obs_path) as f:
        bad_feed = json.load(f)
    print(f"Failed Verifier Feed Status: {bad_feed.get('status')} ({bad_feed.get('reason_code')})")
    assert bad_feed.get('status') == 'UNOBSERVABLE'
    assert bad_feed.get('reason_code') == 'LABORATORY_RUN_NOT_VERIFIED_PYTHON'
    print("SUCCESS: Failed verifier yields UNOBSERVABLE.")

if __name__ == "__main__":
    main()
