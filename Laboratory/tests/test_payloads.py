import pytest

def test_input_byte_mutation(baseline_run, run_verifier):
    ledger_dir, runs_dir, run_id = baseline_run
    
    input_file = runs_dir / run_id / "inputs" / "config.json"
    with open(input_file, "w") as f:
        f.write('{"seed": 43}')
        
    report = run_verifier(run_id, ledger_dir, runs_dir)
    assert report["overall_status"] == "FAIL"
    fail_checks = [c for c in report["checks"] if c["status"] == "FAIL"]
    assert any(c["name"] == "inputs_manifest" for c in fail_checks)

def test_input_deletion(baseline_run, run_verifier):
    ledger_dir, runs_dir, run_id = baseline_run
    
    input_file = runs_dir / run_id / "inputs" / "config.json"
    input_file.unlink()
        
    report = run_verifier(run_id, ledger_dir, runs_dir)
    assert report["overall_status"] == "FAIL"
    fail_checks = [c for c in report["checks"] if c["status"] == "FAIL"]
    assert any(c["name"] == "inputs_manifest" for c in fail_checks)

def test_input_addition(baseline_run, run_verifier):
    ledger_dir, runs_dir, run_id = baseline_run
    
    input_file = runs_dir / run_id / "inputs" / "extra.json"
    with open(input_file, "w") as f:
        f.write('{"extra": true}')
        
    report = run_verifier(run_id, ledger_dir, runs_dir)
    assert report["overall_status"] == "FAIL"
    fail_checks = [c for c in report["checks"] if c["status"] == "FAIL"]
    assert any(c["name"] == "inputs_manifest" for c in fail_checks)

def test_stdout_mutation(baseline_run, run_verifier):
    ledger_dir, runs_dir, run_id = baseline_run
    
    with open(runs_dir / run_id / "stdout.txt", "w") as f:
        f.write("sneaky string")
        
    report = run_verifier(run_id, ledger_dir, runs_dir)
    assert report["overall_status"] == "FAIL"
    fail_checks = [c for c in report["checks"] if c["status"] == "FAIL"]
    assert any(c["name"] == "stdout_hash" for c in fail_checks)
