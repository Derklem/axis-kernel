import pytest
import json
import threading
from laboratory.cli import run_experiment_cmd
from laboratory.ledger import init_ledger, LedgerLock

def test_cooperative_writers(tmp_path, run_verifier):
    ledger_dir = tmp_path / "ledger"
    runs_dir = tmp_path / "runs"
    init_ledger(ledger_dir)
    
    def run_worker(idx):
        exp_dir = tmp_path / f"exp_{idx}"
        exp_dir.mkdir()
        exp_data = {
            "hypothesis": f"Worker {idx}",
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
        
    threads = []
    for i in range(4):
        t = threading.Thread(target=run_worker, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    with open(ledger_dir / "ledger.jsonl", "r") as f:
        events = [json.loads(line) for line in f if line.strip()]
        
    assert len(events) == 1 + 4*2
    
    seqs = [ev["sequence"] for ev in events]
    assert seqs == list(range(9)), "Sequences must be monotonic without duplicates"
    
    for ev in events[1:]:
        assert ev["previous_hash"] == events[ev["sequence"] - 1]["hash"]
        
    for run_dir in runs_dir.glob("RUN_*"):
        report = run_verifier(run_dir.name, ledger_dir, runs_dir)
        assert report["overall_status"] == "PASS"

def test_lock_contention(tmp_path):
    ledger_dir = tmp_path / "ledger"
    init_ledger(ledger_dir)
    
    lock = LedgerLock(ledger_dir, timeout_seconds=1)
    with pytest.raises(TimeoutError):
        with lock:
            lock2 = LedgerLock(ledger_dir, timeout_seconds=1)
            with lock2:
                pass
