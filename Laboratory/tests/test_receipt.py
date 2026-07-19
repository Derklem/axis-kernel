import pytest
import json

def mutate_receipt(runs_dir, run_id, mutator_fn):
    receipt_file = runs_dir / run_id / "receipt.json"
    with open(receipt_file, "r", encoding="utf-8") as f:
        receipt = json.load(f)
        
    mutator_fn(receipt)
    
    with open(receipt_file, "w", encoding="utf-8") as f:
        json.dump(receipt, f)
        
def test_receipt_field_mutation(baseline_run, run_verifier):
    ledger_dir, runs_dir, run_id = baseline_run
    
    def mutate(r):
        r["environment"]["os"] = "TempleOS"
        
    mutate_receipt(runs_dir, run_id, mutate)
    report = run_verifier(run_id, ledger_dir, runs_dir)
    assert report["overall_status"] == "FAIL"
    fail_checks = [c for c in report["checks"] if c["status"] == "FAIL"]
    assert any(c["name"] == "receipt_hash" for c in fail_checks)

def test_receipt_undeclared_property(baseline_run, run_verifier):
    ledger_dir, runs_dir, run_id = baseline_run
    
    def mutate(r):
        r["sneaky_backdoor"] = True
        
    mutate_receipt(runs_dir, run_id, mutate)
    report = run_verifier(run_id, ledger_dir, runs_dir)
    assert report["overall_status"] == "FAIL"
    fail_checks = [c for c in report["checks"] if c["status"] == "FAIL"]
    assert any(c["name"] == "receipt_schema" for c in fail_checks)

def test_receipt_missing_property(baseline_run, run_verifier):
    ledger_dir, runs_dir, run_id = baseline_run
    
    def mutate(r):
        del r["run_id"]
        
    mutate_receipt(runs_dir, run_id, mutate)
    report = run_verifier(run_id, ledger_dir, runs_dir)
    assert report["overall_status"] == "FAIL"
    fail_checks = [c for c in report["checks"] if c["status"] == "FAIL"]
    assert any(c["name"] == "receipt_schema" for c in fail_checks)
