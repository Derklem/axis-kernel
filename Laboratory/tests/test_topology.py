import pytest
import shutil
import json
from laboratory.cli import run_experiment_cmd
from laboratory.ledger import init_ledger

def test_evil_twin(tmp_path, run_verifier):
    ledger_dir = tmp_path / "ledger"
    runs_dir = tmp_path / "runs"
    
    init_ledger(ledger_dir)
    
    exp_dir = tmp_path / "hello_world"
    exp_dir.mkdir()
    
    exp_data = {
        "hypothesis": "Test",
        "procedure": "Test",
        "adapter": {
            "type": "subprocess",
            "command": ["python", "-c", "print('hello')"]
        },
        "evaluation_criteria": {
            "deterministic_checks": [
                {"name": "exit_code_equals", "expected_exit_code": 0}
            ]
        }
    }
    with open(exp_dir / "experiment.json", "w", encoding="utf-8") as f:
        json.dump(exp_data, f)
        
    run_experiment_cmd(exp_dir, ledger_dir, runs_dir)
    
    run_dirs = list(runs_dir.glob("RUN_*"))
    assert len(run_dirs) == 1
    run_id = run_dirs[0].name
    
    evil_twin_id = run_id.replace(run_id[-4:], "6666") 
    evil_twin_dir = runs_dir / evil_twin_id
    shutil.copytree(runs_dir / run_id, evil_twin_dir)
    
    receipt_file = evil_twin_dir / "receipt.json"
    with open(receipt_file, "r") as f:
        receipt = json.load(f)
    receipt["run_id"] = evil_twin_id
    with open(receipt_file, "w") as f:
        json.dump(receipt, f)
        
    report = run_verifier(evil_twin_id, ledger_dir, runs_dir)
    assert report["overall_status"] == "UNVERIFIABLE"
    fail_checks = [c for c in report["checks"] if c["status"] == "UNVERIFIABLE"]
    assert any(c["name"] == "run_started_event" for c in fail_checks)

def test_cross_contamination(tmp_path, run_verifier):
    ledger_dir = tmp_path / "ledger"
    runs_dir = tmp_path / "runs"
    init_ledger(ledger_dir)
    
    # Run A
    exp_a = tmp_path / "exp_a"
    exp_a.mkdir()
    with open(exp_a / "experiment.json", "w", encoding="utf-8") as f:
        json.dump({
            "hypothesis": "A",
            "procedure": "A",
            "adapter": {"type": "subprocess", "command": ["python", "-c", "print('A')"]},
            "evaluation_criteria": {"deterministic_checks": [{"name": "exit_code_equals", "expected_exit_code": 0}]}
        }, f)
    run_experiment_cmd(exp_a, ledger_dir, runs_dir)
    
    # Run B
    exp_b = tmp_path / "exp_b"
    exp_b.mkdir()
    with open(exp_b / "experiment.json", "w", encoding="utf-8") as f:
        json.dump({
            "hypothesis": "B",
            "procedure": "B",
            "adapter": {"type": "subprocess", "command": ["python", "-c", "print('B')"]},
            "evaluation_criteria": {"deterministic_checks": [{"name": "exit_code_equals", "expected_exit_code": 0}]}
        }, f)
    run_experiment_cmd(exp_b, ledger_dir, runs_dir)
    
    run_dirs = list(runs_dir.glob("RUN_*"))
    assert len(run_dirs) == 2
    
    receipt_a = run_dirs[0] / "receipt.json"
    receipt_b = run_dirs[1] / "receipt.json"
    
    # Swap receipts
    temp_path = tmp_path / "temp.json"
    shutil.move(receipt_a, temp_path)
    shutil.move(receipt_b, receipt_a)
    shutil.move(temp_path, receipt_b)
    
    report_a = run_verifier(run_dirs[0].name, ledger_dir, runs_dir)
    assert report_a["overall_status"] == "FAIL"
