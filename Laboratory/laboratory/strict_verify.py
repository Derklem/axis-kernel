import json
import subprocess
import sys
from pathlib import Path
from laboratory.verifier import verify_run
from laboratory.crypto import canonical_hash

def normalize_verification_report(report: dict) -> dict:
    normalized_checks = []
    # Sort checks by name to ensure stable ordering
    sorted_checks = sorted(report.get("checks", []), key=lambda x: x["name"])
    
    for check in sorted_checks:
        norm_check = {
            "name": check["name"],
            "status": check["status"]
        }
        if "expected" in check:
            norm_check["expected"] = check["expected"]
        if "observed" in check:
            norm_check["observed"] = check["observed"]
        normalized_checks.append(norm_check)
        
    return {
        "run_id": report["run_id"],
        "overall_status": report["overall_status"],
        "checks": normalized_checks
    }

def verify_strict_run(run_id: str, ledger_dir: Path, runs_dir: Path, rust_verifier_path: Path) -> dict:
    python_report = verify_run(run_id, ledger_dir, runs_dir)
    
    res = subprocess.run([
        str(rust_verifier_path), run_id, 
        "--ledger-dir", str(ledger_dir), 
        "--runs-dir", str(runs_dir)
    ], capture_output=True, text=True)
    
    if res.returncode not in (0, 1, 3):
        # Unhandled Rust error
        rust_report = {
            "run_id": run_id,
            "overall_status": "FAIL",
            "checks": [{"name": "rust_execution", "status": "FAIL"}]
        }
    else:
        try:
            rust_report = json.loads(res.stdout)
        except json.JSONDecodeError:
            rust_report = {
                "run_id": run_id,
                "overall_status": "FAIL",
                "checks": [{"name": "rust_execution", "status": "FAIL"}]
            }
            
    py_norm = normalize_verification_report(python_report)
    rs_norm = normalize_verification_report(rust_report)
    
    py_root = canonical_hash(py_norm)
    rs_root = canonical_hash(rs_norm)
    
    reports_equal = (py_root == rs_root)
    
    receipt_path = runs_dir / run_id / "receipt.json"
    if receipt_path.exists():
        with open(receipt_path, "r", encoding="utf-8") as f:
            receipt = json.load(f)
        receipt_hash = canonical_hash(receipt)
    else:
        receipt_hash = "0" * 64
        
    verification_artifact = {
        "verification_schema_version": "1.0.0",
        "run_id": run_id,
        "receipt_hash": receipt_hash,
        "python_verifier": {
            "result": python_report["overall_status"],
            "report_root": py_root
        },
        "rust_verifier": {
            "result": rust_report.get("overall_status", "FAIL"),
            "report_root": rs_root
        },
        "normalized_reports_equal": reports_equal
    }
    
    return verification_artifact
