import os
import json
import subprocess
from pathlib import Path

CORPUS_DIR = Path("corpus/0.1.0")
RUST_VERIFIER_CMD = ["verifier-rs/target/debug/verifier-rs.exe"]
PYTHON_VERIFIER_CMD = ["python", "-m", "laboratory.cli", "verify", "--json"]

def run_verifier(cmd, case_dir, run_id):
    ledger_dir = case_dir / "ledger"
    runs_dir = case_dir / "runs"
    
    full_cmd = cmd + [
        run_id,
        "--ledger-dir" if "verifier-rs" in str(cmd) else "--dir", str(ledger_dir),
        "--runs-dir", str(runs_dir)
    ]
    
    result = subprocess.run(full_cmd, capture_output=True, text=True)
    
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Failed to parse JSON from {' '.join(cmd)}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        return None, result.returncode
        
    return parsed, result.returncode

def normalize(report):
    return {
        "run_id": report["run_id"],
        "overall_status": report["overall_status"],
        "checks": [
            {
                "name": c["name"],
                "status": c["status"]
            }
            for c in report["checks"]
        ]
    }

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--rust-binary", default="verifier-rs/target/debug/verifier-rs.exe")
    args = parser.parse_args()
    
    global RUST_VERIFIER_CMD
    RUST_VERIFIER_CMD = [args.rust_binary]

    if not CORPUS_DIR.exists():
        print(f"Corpus not found at {CORPUS_DIR}")
        import sys
        sys.exit(1)
        
    import hashlib
    def raw_hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    manifest_path = Path("corpus") / "0.1.0_manifest.json"
    if not manifest_path.exists():
        print(f"Manifest not found at {manifest_path}")
        import sys
        sys.exit(1)
        
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    print("Verifying corpus manifest integrity...")
    manifest_failures = 0
    declared_files = set(manifest.get("files", {}).keys())
    
    actual_files = {
        p.relative_to(CORPUS_DIR).as_posix()
        for p in CORPUS_DIR.rglob("*")
        if p.is_file()
    }
    
    missing = declared_files - actual_files
    unexpected = actual_files - declared_files
    
    if missing or unexpected:
        print(f"  [FAIL] Corpus file-set mismatch")
        if missing:
            print(f"    Missing: {sorted(missing)}")
        if unexpected:
            print(f"    Unexpected: {sorted(unexpected)}")
        import sys
        sys.exit(1)
        
    for rel_path, expected_hash in manifest.get("files", {}).items():
        p = CORPUS_DIR / rel_path
        actual_hash = raw_hash_file(p)
        if actual_hash != expected_hash:
            print(f"  [FAIL] Hash mismatch: {rel_path}")
            manifest_failures += 1
            
    if manifest_failures > 0:
        print("Corpus manifest verification failed. Aborting.")
        import sys
        sys.exit(1)
        
    if manifest.get("protocol_version") != "0.1.0" or manifest.get("corpus_version") != "0.1.0":
        print("Manifest version mismatch. Expected protocol 0.1.0 and corpus 0.1.0")
        import sys
        sys.exit(1)
        
    cases = list(CORPUS_DIR.glob("*/*"))
    
    expected_exit_codes = {
        "PASS": 0,
        "FAIL": 1,
        "UNVERIFIABLE": 3
    }
    
    failures = 0
    
    for case_dir in cases:
        if not case_dir.is_dir(): continue
        
        metadata_file = case_dir / "metadata.json"
        with open(metadata_file) as f:
            metadata = json.load(f)
            
        run_id = metadata["run_id"]
        expected = metadata["expected"]
        exp_code = expected_exit_codes[expected]
        
        print(f"Running {case_dir.parent.name}/{case_dir.name}...")
        
        py_out, py_code = run_verifier(PYTHON_VERIFIER_CMD, case_dir, run_id)
        rs_out, rs_code = run_verifier(RUST_VERIFIER_CMD, case_dir, run_id)
        
        if py_out is None or rs_out is None:
            print(f"  [ERROR] Failed to execute implementations.")
            failures += 1
            continue
            
        # Check exit codes
        if py_code != exp_code or rs_code != exp_code:
            print(f"  [FAIL] Exit code mismatch. Py: {py_code}, Rs: {rs_code}, Expected: {exp_code}")
            failures += 1
            continue
            
        if py_out["overall_status"] != expected or rs_out["overall_status"] != expected:
            print(f"  [FAIL] Overall status mismatch. Py: {py_out.get('overall_status')}, Rs: {rs_out.get('overall_status')}, Expected: {expected}")
            failures += 1
            continue
            
        # Check exact normalized report parity
        norm_py = normalize(py_out)
        norm_rs = normalize(rs_out)
        
        if norm_py != norm_rs:
            print(f"  [FAIL] Complete normalized report mismatch.")
            print(f"    Py: {json.dumps(norm_py, ensure_ascii=False)}")
            print(f"    Rs: {json.dumps(norm_rs, ensure_ascii=False)}")
            failures += 1
            continue
            
        print(f"  [OK] Python and Rust implementations match perfectly ({expected})")
        
    print(f"\nConformance suite complete. {failures} failures.")
    if failures > 0:
        import sys
        sys.exit(1)

if __name__ == "__main__":
    main()
