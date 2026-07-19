import pytest
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple
from laboratory.cli import run_experiment_cmd
from laboratory.ledger import init_ledger

@pytest.fixture(scope="function")
def baseline_run(tmp_path):
    """
    Sets up a temporary directory with a valid ledger and a completed hello_world run.
    Yields (ledger_dir, runs_dir, run_id).
    """
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
        
    (exp_dir / "inputs").mkdir()
    with open(exp_dir / "inputs" / "config.json", "w", encoding="utf-8") as f:
        f.write('{"seed": 42}')
        
    run_experiment_cmd(exp_dir, ledger_dir, runs_dir)
    
    run_dirs = list(runs_dir.glob("RUN_*"))
    assert len(run_dirs) == 1
    run_id = run_dirs[0].name
    
    yield ledger_dir, runs_dir, run_id

@pytest.fixture
def run_verifier():
    def _run(run_id: str, ledger_dir: Path, runs_dir: Path):
        from laboratory.verifier import verify_run
        return verify_run(run_id, ledger_dir, runs_dir)
    return _run
