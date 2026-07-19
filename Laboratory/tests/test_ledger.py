import pytest
import json
from laboratory.crypto import canonical_hash

def mutate_ledger_tail(ledger_file, mutator_fn):
    lines = []
    with open(ledger_file, "r") as f:
        for line in f:
            if line.strip():
                lines.append(json.loads(line))
                
    mutator_fn(lines)
    
    with open(ledger_file, "w") as f:
        for ev in lines:
            f.write(json.dumps(ev, separators=(',', ':'), sort_keys=True) + "\n")

def test_ledger_payload_mutation(baseline_run, run_verifier):
    ledger_dir, runs_dir, run_id = baseline_run
    
    def mutate(lines):
        lines[-1]["payload"]["receipt_hash"] = "0" * 64
        
    mutate_ledger_tail(ledger_dir / "ledger.jsonl", mutate)
    report = run_verifier(run_id, ledger_dir, runs_dir)
    assert report["overall_status"] == "FAIL"
    fail_checks = [c for c in report["checks"] if c["status"] == "FAIL"]
    assert any("Hash mismatch" in c.get("detail", "") for c in fail_checks)
    
def test_ledger_truncation(baseline_run, run_verifier):
    ledger_dir, runs_dir, run_id = baseline_run
    ledger_file = ledger_dir / "ledger.jsonl"
    
    with open(ledger_file, "r") as f:
        content = f.read()
        
    with open(ledger_file, "w") as f:
        f.write(content[:-10])
        
    report = run_verifier(run_id, ledger_dir, runs_dir)
    assert report["overall_status"] == "FAIL"
    fail_checks = [c for c in report["checks"] if c["status"] == "FAIL"]
    assert any("valid JSONL" in c.get("detail", "") for c in fail_checks)

def test_duplicate_run_started(baseline_run, run_verifier):
    ledger_dir, runs_dir, run_id = baseline_run
    
    def mutate(lines):
        start_event = lines[1].copy()
        start_event["sequence"] = lines[-1]["sequence"] + 1
        start_event["previous_hash"] = lines[-1]["hash"]
        test_ev = start_event.copy()
        test_ev.pop("hash", None)
        start_event["hash"] = canonical_hash(test_ev)
        lines.append(start_event)
        
    mutate_ledger_tail(ledger_dir / "ledger.jsonl", mutate)
    report = run_verifier(run_id, ledger_dir, runs_dir)
    assert report["overall_status"] == "FAIL"
    fail_checks = [c for c in report["checks"] if c["status"] == "FAIL"]
    assert any(c["name"] == "run_started_event" for c in fail_checks)

def test_orphaned_run_started(baseline_run, run_verifier):
    ledger_dir, runs_dir, run_id = baseline_run
    
    def mutate(lines):
        lines.pop() # Remove RUN_COMPLETED
        
    mutate_ledger_tail(ledger_dir / "ledger.jsonl", mutate)
    report = run_verifier(run_id, ledger_dir, runs_dir)
    assert report["overall_status"] == "UNVERIFIABLE"
    fail_checks = [c for c in report["checks"] if c["status"] == "UNVERIFIABLE"]
    assert any(c["name"] == "terminal_event" for c in fail_checks)
