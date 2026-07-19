import pytest
import json
from hypothesis import given, strategies as st
from laboratory.crypto import canonical_hash
from laboratory.verifier import verify_run

def test_invariant_4_monotonic_sequence(baseline_run):
    ledger_dir, runs_dir, run_id = baseline_run
    ledger_file = ledger_dir / "ledger.jsonl"
    
    seqs = []
    with open(ledger_file, "r") as f:
        for line in f:
            if line.strip():
                seqs.append(json.loads(line)["sequence"])
                
    assert seqs == [0, 1, 2]

def test_invariant_5_readonly_verifier(baseline_run):
    ledger_dir, runs_dir, run_id = baseline_run
    run_dir = runs_dir / run_id
    
    def get_mtimes():
        mtimes = {}
        for p in run_dir.rglob("*"):
            mtimes[p] = p.stat().st_mtime
        mtimes[ledger_dir / "ledger.jsonl"] = (ledger_dir / "ledger.jsonl").stat().st_mtime
        return mtimes
        
    before = get_mtimes()
    verify_run(run_id, ledger_dir, runs_dir)
    after = get_mtimes()
    
    assert before == after, "Verifier modified the filesystem!"

@given(st.dictionaries(keys=st.text(), values=st.text()))
def test_invariant_8_canonical_hashing_property(d):
    """
    Identical logical objects produce identical hashes, regardless of key insertion order.
    """
    d1 = d.copy()
    d2 = {k: d1[k] for k in sorted(d1.keys(), reverse=True)} # Reverse order insertion
    assert d1 == d2 # Python dict equality
    assert canonical_hash(d1) == canonical_hash(d2)

def test_baseline_golden_path(baseline_run, run_verifier):
    ledger_dir, runs_dir, run_id = baseline_run
    report = run_verifier(run_id, ledger_dir, runs_dir)
    assert report["overall_status"] == "PASS"
