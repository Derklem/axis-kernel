import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List
import jsonschema
from laboratory.crypto import canonical_hash

def hash_file(path: Path) -> str:
    if not path.exists(): return ""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def verify_run(run_id: str, ledger_dir: Path, runs_dir: Path) -> Dict[str, Any]:
    checks = []
    overall_status = "PASS"
    
    def add_check(name: str, status: str, detail: str = None, expected: Any = None, observed: Any = None):
        nonlocal overall_status
        check = {"name": name, "status": status}
        if detail: check["detail"] = detail
        if expected is not None: check["expected"] = expected
        if observed is not None: check["observed"] = observed
        checks.append(check)
        
        # FAIL > UNVERIFIABLE > PASS
        if status == "FAIL":
            overall_status = "FAIL"
        elif status == "UNVERIFIABLE" and overall_status == "PASS":
            overall_status = "UNVERIFIABLE"
            
    # 1. ledger_load
    ledger_file = ledger_dir / "ledger.jsonl"
    if not ledger_file.exists():
        add_check("ledger_load", "UNVERIFIABLE", detail="Ledger file missing")
        return {"run_id": run_id, "overall_status": overall_status, "checks": checks}
        
    events = []
    try:
        with open(ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
        add_check("ledger_load", "PASS")
    except json.JSONDecodeError:
        add_check("ledger_load", "FAIL", detail="Ledger file is not valid JSONL")
        return {"run_id": run_id, "overall_status": overall_status, "checks": checks}

    # 2. ledger_chain
    event_schema_path = Path(__file__).parent / "schemas" / "event_schema.json"
    with open(event_schema_path, "r", encoding="utf-8") as f:
        event_schema = json.load(f)
        
    expected_sequence = 0
    expected_prev_hash = None
    chain_valid = True
    
    for idx, event in enumerate(events):
        try:
            jsonschema.validate(instance=event, schema=event_schema)
        except jsonschema.exceptions.ValidationError as e:
            add_check("ledger_chain", "FAIL", detail=f"Event {idx} schema validation failed: {e.message}")
            chain_valid = False
            break
            
        if event["sequence"] != expected_sequence:
            add_check("ledger_chain", "FAIL", detail=f"Sequence gap at index {idx}", expected=expected_sequence, observed=event["sequence"])
            chain_valid = False
            break
            
        if event["previous_hash"] != expected_prev_hash:
            add_check("ledger_chain", "FAIL", detail=f"Hash chain broken at index {idx}", expected=expected_prev_hash, observed=event["previous_hash"])
            chain_valid = False
            break
            
        test_event = event.copy()
        stored_hash = test_event.pop("hash", None)
        try:
            recomputed = canonical_hash(test_event)
        except ValueError as e:
            add_check("ledger_chain", "FAIL", detail=f"Canonicalization failed at index {idx}: {e}")
            chain_valid = False
            break
            
        if stored_hash != recomputed:
            add_check("ledger_chain", "FAIL", detail=f"Hash mismatch at index {idx}", expected=stored_hash, observed=recomputed)
            chain_valid = False
            break
            
        expected_sequence += 1
        expected_prev_hash = stored_hash
        
    if chain_valid:
        add_check("ledger_chain", "PASS")
    else:
        return {"run_id": run_id, "overall_status": overall_status, "checks": checks}
        
    # 3. run_started_event
    run_started_events = [e for e in events if e.get("event_type") == "RUN_STARTED" and e.get("payload", {}).get("run_id") == run_id]
    if len(run_started_events) != 1:
        add_check("run_started_event", "FAIL" if len(run_started_events) > 1 else "UNVERIFIABLE", expected=1, observed=len(run_started_events))
        return {"run_id": run_id, "overall_status": overall_status, "checks": checks}
    start_event = run_started_events[0]
    add_check("run_started_event", "PASS")
    
    # 4. terminal_event
    terminal_types = {"RUN_COMPLETED", "RUN_FAILED", "RUN_ABORTED"}
    terminal_events = [e for e in events if e.get("event_type") in terminal_types and e.get("payload", {}).get("run_id") == run_id]
    if len(terminal_events) != 1:
        add_check("terminal_event", "FAIL" if len(terminal_events) > 1 else "UNVERIFIABLE", expected=1, observed=len(terminal_events))
        return {"run_id": run_id, "overall_status": overall_status, "checks": checks}
    term_event = terminal_events[0]
    add_check("terminal_event", "PASS")
    
    # 5. terminal_event_sequence
    if term_event["sequence"] <= start_event["sequence"]:
        add_check("terminal_event_sequence", "FAIL", detail="Terminal event occurs before RUN_STARTED")
    else:
        add_check("terminal_event_sequence", "PASS")

    # 6. receipt_presence
    run_dir = runs_dir / run_id
    receipt_path = run_dir / "receipt.json"
    if not receipt_path.exists():
        add_check("receipt_presence", "UNVERIFIABLE", detail="Receipt file missing")
        return {"run_id": run_id, "overall_status": overall_status, "checks": checks}
    
    try:
        with open(receipt_path, "r", encoding="utf-8") as f:
            receipt = json.load(f)
        add_check("receipt_presence", "PASS")
    except json.JSONDecodeError:
        add_check("receipt_presence", "FAIL", detail="Receipt invalid JSON")
        return {"run_id": run_id, "overall_status": overall_status, "checks": checks}
        
    # 7. receipt_schema
    receipt_schema_path = Path(__file__).parent / "schemas" / "receipt.json"
    with open(receipt_schema_path, "r", encoding="utf-8") as f:
        receipt_schema = json.load(f)
        
    try:
        jsonschema.validate(instance=receipt, schema=receipt_schema)
        add_check("receipt_schema", "PASS")
    except jsonschema.exceptions.ValidationError as e:
        add_check("receipt_schema", "FAIL", detail=e.message)
        return {"run_id": run_id, "overall_status": overall_status, "checks": checks}
        
    # 8. receipt_hash
    stored_receipt_hash = term_event["payload"].get("receipt_hash")
    try:
        recomputed_receipt_hash = canonical_hash(receipt)
    except ValueError as e:
        add_check("receipt_hash", "FAIL", detail=f"Canonicalization failed: {e}")
        return {"run_id": run_id, "overall_status": overall_status, "checks": checks}
        
    if stored_receipt_hash != recomputed_receipt_hash:
        add_check("receipt_hash", "FAIL", expected=stored_receipt_hash, observed=recomputed_receipt_hash)
    else:
        add_check("receipt_hash", "PASS")
        
    # 9. run_started_link
    if receipt.get("run_started_hash") != start_event["hash"]:
        add_check("run_started_link", "FAIL", expected=start_event["hash"], observed=receipt.get("run_started_hash"))
    else:
        add_check("run_started_link", "PASS")
        
    # 10. experiment_presence
    exp_path = run_dir / "experiment.json"
    if not exp_path.exists():
        add_check("experiment_presence", "UNVERIFIABLE", detail="experiment.json missing")
        return {"run_id": run_id, "overall_status": overall_status, "checks": checks}
        
    try:
        with open(exp_path, "r", encoding="utf-8") as f:
            experiment = json.load(f)
        add_check("experiment_presence", "PASS")
    except json.JSONDecodeError:
        add_check("experiment_presence", "FAIL", detail="Experiment invalid JSON")
        return {"run_id": run_id, "overall_status": overall_status, "checks": checks}
        
    # 11. experiment_schema
    experiment_schema_path = Path(__file__).parent / "schemas" / "experiment.json"
    with open(experiment_schema_path, "r", encoding="utf-8") as f:
        experiment_schema = json.load(f)
        
    try:
        jsonschema.validate(instance=experiment, schema=experiment_schema)
        add_check("experiment_schema", "PASS")
    except jsonschema.exceptions.ValidationError as e:
        add_check("experiment_schema", "FAIL", detail=e.message)
        return {"run_id": run_id, "overall_status": overall_status, "checks": checks}

    # 12. experiment_hash
    stored_exp_hash = receipt.get("experiment_hash")
    try:
        recomputed_exp_hash = canonical_hash(experiment)
    except ValueError as e:
        add_check("experiment_hash", "FAIL", detail=f"Canonicalization failed: {e}")
        return {"run_id": run_id, "overall_status": overall_status, "checks": checks}
        
    if stored_exp_hash != recomputed_exp_hash:
        add_check("experiment_hash", "FAIL", expected=stored_exp_hash, observed=recomputed_exp_hash)
    else:
        add_check("experiment_hash", "PASS")
        
    # 13. start_experiment_hash
    if start_event["payload"].get("experiment_hash") != recomputed_exp_hash:
        add_check("start_experiment_hash", "FAIL", expected=start_event["payload"].get("experiment_hash"), observed=recomputed_exp_hash)
    else:
        add_check("start_experiment_hash", "PASS")
        
    # 14. inputs_manifest
    inputs_dir = run_dir / "inputs"
    inputs_manifest = receipt.get("inputs", {})
    actual_inputs = set()
    input_hash_or_size_fail = False
    
    if inputs_dir.exists():
        for p in inputs_dir.rglob("*"):
            if p.is_file():
                rel = p.relative_to(inputs_dir).as_posix()
                actual_inputs.add(rel)
                h = hash_file(p)
                s = p.stat().st_size
                manifest_entry = inputs_manifest.get(rel, {})
                expected_h = manifest_entry.get("hash")
                expected_s = manifest_entry.get("size")
                if h != expected_h or s != expected_s:
                    input_hash_or_size_fail = True
    
    expected_inputs = set(inputs_manifest.keys())
    if actual_inputs != expected_inputs or input_hash_or_size_fail:
        add_check("inputs_manifest", "FAIL")
    else:
        add_check("inputs_manifest", "PASS")
        
    # 15. artifacts_manifest
    artifacts_dir = run_dir / "artifacts"
    artifacts_manifest = receipt.get("artifacts", {})
    actual_artifacts = set()
    artifact_hash_fail = False
    
    if artifacts_dir.exists():
        for p in artifacts_dir.rglob("*"):
            if p.is_file():
                rel = p.relative_to(artifacts_dir).as_posix()
                actual_artifacts.add(rel)
                h = hash_file(p)
                expected_h = artifacts_manifest.get(rel)
                if h != expected_h:
                    artifact_hash_fail = True
                    
    expected_artifacts = set(artifacts_manifest.keys())
    if actual_artifacts != expected_artifacts or artifact_hash_fail:
        add_check("artifacts_manifest", "FAIL")
    else:
        add_check("artifacts_manifest", "PASS")
        
    # 16. stdout_hash
    stdout_hash = hash_file(run_dir / "stdout.txt")
    if stdout_hash != receipt["execution"].get("stdout_hash", ""):
        add_check("stdout_hash", "FAIL", expected=receipt["execution"].get("stdout_hash"), observed=stdout_hash)
    else:
        add_check("stdout_hash", "PASS")
        
    # 17. stderr_hash
    stderr_hash = hash_file(run_dir / "stderr.txt")
    if stderr_hash != receipt["execution"].get("stderr_hash", ""):
        add_check("stderr_hash", "FAIL", expected=receipt["execution"].get("stderr_hash"), observed=stderr_hash)
    else:
        add_check("stderr_hash", "PASS")
        
    return {"run_id": run_id, "overall_status": overall_status, "checks": checks}
