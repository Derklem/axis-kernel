import argparse
import sys
import json
import shutil
import platform
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from laboratory.ledger import init_ledger, append_event
from laboratory.crypto import generate_uuid, canonical_hash
from laboratory.runner import run_experiment
from laboratory.verifier import verify_run
import jsonschema

def hash_file(path: Path) -> str:
    if not path.exists(): return ""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def run_experiment_cmd(experiment_dir_path: Path, ledger_dir: Path, runs_dir: Path):
    if not experiment_dir_path.exists():
        print(f"[ERROR] Experiment directory not found: {experiment_dir_path}")
        sys.exit(1)
        
    exp_file = experiment_dir_path / "experiment.json"
    if not exp_file.exists():
        print(f"[ERROR] Missing experiment.json in {experiment_dir_path}")
        sys.exit(1)
        
    with open(exp_file, "r", encoding="utf-8") as f:
        experiment = json.load(f)
        
    schema_path = Path(__file__).parent / "schemas" / "experiment.json"
    if schema_path.exists():
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        try:
            jsonschema.validate(instance=experiment, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            print(f"[ERROR] Invalid experiment.json: {e.message}")
            sys.exit(1)
            
    exp_hash = canonical_hash(experiment)
    run_id = f"RUN_{generate_uuid()}"
    run_path = runs_dir / run_id
    run_path.mkdir(parents=True, exist_ok=True)
    
    shutil.copy2(exp_file, run_path / "experiment.json")
    
    inputs_dir = experiment_dir_path / "inputs"
    inputs_manifest = {}
    if inputs_dir.exists() and inputs_dir.is_dir():
        run_inputs_dir = run_path / "inputs"
        shutil.copytree(inputs_dir, run_inputs_dir)
        for input_file in run_inputs_dir.rglob("*"):
            if input_file.is_file():
                file_hash = hash_file(input_file)
                file_size = input_file.stat().st_size
                rel_path = input_file.relative_to(run_inputs_dir).as_posix()
                inputs_manifest[rel_path] = {
                    "hash": file_hash,
                    "size": file_size,
                    "mime": "application/octet-stream",
                    "description": ""
                }
                
    env = {
        "os": platform.system(),
        "python_version": platform.python_version(),
        "hostname": platform.node(),
        "working_directory": str(experiment_dir_path.resolve()),
        "adapter_version": experiment.get("adapter", {}).get("type", "unknown"),
        "git_commit": "unknown",
        "git_dirty": False,
        "additional_metadata": {}
    }
    
    try:
        start_event = append_event(ledger_dir, "RUN_STARTED", {
            "run_id": run_id,
            "experiment_hash": exp_hash
        })
        start_event_hash = start_event["hash"]
        print(f"[SUCCESS] RUN_STARTED emitted to ledger. Run ID: {run_id}")
    except Exception as e:
        print(f"[ERROR] Could not write RUN_STARTED to ledger: {e}")
        sys.exit(1)
        
    # Setup artifacts directory
    artifacts_dir = run_path / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    
    # Pre-execution validation of expected artifacts
    expected_artifacts = experiment.get("expected_artifacts", [])
    for art in expected_artifacts:
        art_path = (artifacts_dir / art).resolve()
        try:
            art_path.relative_to(artifacts_dir.resolve())
        except ValueError:
            print(f"[ERROR] Expected artifact path '{art}' escapes the artifacts directory.")
            sys.exit(1)
    
    adapter = experiment.get("adapter", {})
    command = adapter.get("command", [])
    timeout = adapter.get("timeout_seconds", 300)
    
    stdout_path = run_path / "stdout.txt"
    stderr_path = run_path / "stderr.txt"
    
    run_env = {
        "LAB_RUN_ID": run_id,
        "LAB_ARTIFACTS_DIR": str(artifacts_dir.resolve())
    }
    
    started_at = datetime.now(timezone.utc).isoformat()
    result = run_experiment(command, str(stdout_path), str(stderr_path), str(experiment_dir_path), run_env, timeout_seconds=timeout)
    completed_at = datetime.now(timezone.utc).isoformat()
    
    stdout_hash = hash_file(stdout_path)
    stderr_hash = hash_file(stderr_path)
    
    missing_artifacts = []
    for art in expected_artifacts:
        art_path = artifacts_dir / art
        if not art_path.exists():
            missing_artifacts.append(art)
            
    artifacts_manifest = {}
    for art_file in artifacts_dir.rglob("*"):
        if art_file.is_file():
            rel_path = art_file.relative_to(artifacts_dir).as_posix()
            artifacts_manifest[rel_path] = hash_file(art_file)
            
    deterministic_checks = experiment.get("evaluation_criteria", {}).get("deterministic_checks", [])
    eval_results = []
    overall_result = True
    for check in deterministic_checks:
        name = check.get("name")
        expected_code = check.get("expected_exit_code")
        if name == "exit_code_equals":
            passed = (result["exit_code"] == expected_code)
            eval_results.append({
                "check": name,
                "passed": passed,
                "expected": expected_code,
                "observed": result["exit_code"]
            })
            if not passed:
                overall_result = False
                
    if missing_artifacts:
        overall_result = False
        eval_results.append({
            "check": "expected_artifacts_exist",
            "passed": False,
            "expected": len(expected_artifacts),
            "observed": len(expected_artifacts) - len(missing_artifacts)
        })
                
    receipt = {
        "receipt_schema_version": "1.0.0",
        "laboratory_version": "0.1.0",
        "run_id": run_id,
        "parent_run_id": None,
        "run_started_hash": start_event_hash,
        "experiment_hash": exp_hash,
        "hash_algorithm": "sha256",
        "timestamps": {
            "started_at": started_at,
            "completed_at": completed_at
        },
        "environment": env,
        "inputs": inputs_manifest,
        "execution": {
            "status": result["status"],
            "exit_code": result["exit_code"],
            "stdout_hash": stdout_hash,
            "stderr_hash": stderr_hash
        },
        "artifacts": artifacts_manifest,
        "evaluation": {
            "deterministic_results": eval_results,
            "overall_result": overall_result,
            "subjective_notes": ""
        }
    }
    
    receipt_hash = canonical_hash(receipt)
    receipt_path = run_path / "receipt.json"
    
    with open(receipt_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(receipt, separators=(',', ':'), sort_keys=True) + "\n")
        
    status_to_event = {
        "COMPLETED": "RUN_COMPLETED",
        "FAILED": "RUN_FAILED",
        "ABORTED": "RUN_ABORTED"
    }
    event_type = status_to_event.get(result["status"], "RUN_ABORTED")
    if result["status"] == "COMPLETED" and result.get("exit_code") != 0:
        event_type = "RUN_FAILED"
        
    rel_receipt_path = f"data/runs/{run_id}/receipt.json"
        
    try:
        append_event(ledger_dir, event_type, {
            "run_id": run_id,
            "receipt_hash": receipt_hash,
            "receipt_path": rel_receipt_path
        })
        print(f"[SUCCESS] {event_type}. Ledger appended.")
    except Exception as e:
        print(f"[ERROR] Could not write {event_type} to ledger: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Laboratory Evidence Protocol CLI")
    parser.add_argument("--version", action="version", version="Laboratory v0.1.0")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Initialize the evidence ledger")
    init_parser.add_argument("--dir", type=str, default="data/ledger", help="Ledger directory")

    run_parser = subparsers.add_parser("run", help="Run an experiment and freeze evidence")
    run_parser.add_argument("experiment_dir", type=str, help="Path to the experiment directory")
    run_parser.add_argument("--dir", type=str, default="data/ledger", help="Ledger directory")
    run_parser.add_argument("--runs-dir", type=str, default="data/runs", help="Runs directory")
    
    verify_parser = subparsers.add_parser("verify", help="Verify a run against the ledger")
    verify_parser.add_argument("run_id", type=str, help="Run ID to verify")
    verify_parser.add_argument("--dir", type=str, default="data/ledger", help="Ledger directory")
    verify_parser.add_argument("--runs-dir", type=str, default="data/runs", help="Runs directory")
    verify_parser.add_argument("--json", action="store_true", help="Output JSON report")

    verify_strict_parser = subparsers.add_parser("verify-strict", help="Strictly verify a run using Python and Rust verifiers")
    verify_strict_parser.add_argument("run_id", type=str, help="Run ID to verify")
    verify_strict_parser.add_argument("--rust-verifier", type=str, required=True, help="Path to rust verifier binary")
    verify_strict_parser.add_argument("--dir", type=str, default="data/ledger", help="Ledger directory")
    verify_strict_parser.add_argument("--runs-dir", type=str, default="data/runs", help="Runs directory")
    verify_strict_parser.add_argument("--json", action="store_true", help="Output JSON verification artifact")


    args = parser.parse_args()

    if args.command == "init":
        ledger_dir = Path(args.dir).resolve()
        try:
            event_hash = init_ledger(ledger_dir)
            print(f"[SUCCESS] Ledger initialized successfully\n")
            print(f"Ledger Path: {ledger_dir}/ledger.jsonl")
            print(f"Genesis Hash: {event_hash}")
        except FileExistsError as e:
            print(f"[ERROR] {e}")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Error initializing ledger: {e}")
            sys.exit(1)
            
    elif args.command == "run":
        experiment_dir = Path(args.experiment_dir).resolve()
        ledger_dir = Path(args.dir).resolve()
        runs_dir = Path(args.runs_dir).resolve()
        run_experiment_cmd(experiment_dir, ledger_dir, runs_dir)
        
    elif args.command == "verify":
        ledger_dir = Path(args.dir).resolve()
        runs_dir = Path(args.runs_dir).resolve()
        report = verify_run(args.run_id, ledger_dir, runs_dir)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"Run ID: {report['run_id']}")
            print(f"Overall Status: {report['overall_status']}\n")
            for check in report['checks']:
                symbol = "[SUCCESS]" if check['status'] == "PASS" else f"[{check['status']}]"
                print(f"{symbol} {check['name']}")
                if 'detail' in check:
                    print(f"    Detail: {check['detail']}")
                if 'expected' in check or 'observed' in check:
                    print(f"    Expected: {check.get('expected')} | Observed: {check.get('observed')}")
                    
        # Exit codes: 0 = PASS, 1 = FAIL, 3 = UNVERIFIABLE
        if report['overall_status'] == "PASS":
            sys.exit(0)
        elif report['overall_status'] == "FAIL":
            sys.exit(1)
        else:
            sys.exit(3)
            
    elif args.command == "verify-strict":
        from laboratory.strict_verify import verify_strict_run
        ledger_dir = Path(args.dir).resolve()
        runs_dir = Path(args.runs_dir).resolve()
        rust_verifier_path = Path(args.rust_verifier).resolve()
        
        artifact = verify_strict_run(args.run_id, ledger_dir, runs_dir, rust_verifier_path)
        
        if args.json:
            print(json.dumps(artifact, indent=2))
        else:
            print(f"Run ID: {artifact['run_id']}")
            print(f"Python Verifier: {artifact['python_verifier']['result']} (Root: {artifact['python_verifier']['report_root'][:8]}...)")
            print(f"Rust Verifier: {artifact['rust_verifier']['result']} (Root: {artifact['rust_verifier']['report_root'][:8]}...)")
            print(f"Normalized Equal: {artifact['normalized_reports_equal']}")
            
        success = (artifact["python_verifier"]["result"] == "PASS" and 
                   artifact["rust_verifier"]["result"] == "PASS" and 
                   artifact["normalized_reports_equal"])
                   
        if success:
            sys.exit(0)
        else:
            sys.exit(1)

        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
