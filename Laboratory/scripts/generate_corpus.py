import os
import json
import shutil
from pathlib import Path
from laboratory.cli import run_experiment_cmd
from laboratory.ledger import init_ledger
from laboratory.crypto import canonical_hash
import hashlib

def raw_hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

CORPUS_DIR = Path("corpus") / "0.1.0"
METADATA_TEMPLATE = {
    "protocol_version": "0.1.0",
    "schema_versions": {
        "event": "1.0.0",
        "receipt": "1.0.0"
    }
}

class MockUUID:
    def __init__(self):
        self.counter = 0
    def uuid4(self):
        self.counter += 1
        return f"00000000-0000-4000-8000-{self.counter:012x}"

mock_uuid = MockUUID()
import laboratory.crypto
laboratory.crypto.generate_uuid = mock_uuid.uuid4

import datetime as dt

class MockDatetime(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 6, 25, 14, 32, mock_uuid.counter % 60, tzinfo=dt.timezone.utc)
    @classmethod
    def utcnow(cls):
        return cls(2026, 6, 25, 14, 32, mock_uuid.counter % 60)

import laboratory.cli
laboratory.cli.datetime = MockDatetime
import laboratory.ledger
laboratory.ledger.datetime = MockDatetime

def setup_baseline(target_dir: Path, custom_exp_data: dict = None) -> str:
    ledger_dir = target_dir / "ledger"
    runs_dir = target_dir / "runs"
    
    init_ledger(ledger_dir)
    
    exp_dir = target_dir / "hello_world"
    exp_dir.mkdir()
    
    exp_data = {
        "hypothesis": "Corpus generation",
        "procedure": "Test",
        "adapter": {
            "type": "subprocess",
            "command": ["python", "-c", "print('hello corpus')"]
        },
        "evaluation_criteria": {
            "deterministic_checks": [
                {"name": "exit_code_equals", "expected_exit_code": 0}
            ]
        }
    }
    if custom_exp_data:
        exp_data.update(custom_exp_data)
        
    with open(exp_dir / "experiment.json", "w", encoding="utf-8") as f:
        json.dump(exp_data, f)
        
    (exp_dir / "inputs").mkdir()
    with open(exp_dir / "inputs" / "config.json", "w", encoding="utf-8") as f:
        f.write('{"key": "value"}')
        
    run_experiment_cmd(exp_dir, ledger_dir, runs_dir)
    
    run_dirs = list(runs_dir.glob("RUN_*"))
    assert len(run_dirs) == 1
    run_id = run_dirs[0].name
    
    shutil.rmtree(exp_dir)
    return run_id

def create_case(category: str, name: str, expected: str, description: str, mutator_fn=None, custom_exp_data=None):
    mock_uuid.counter = 0
    case_dir = CORPUS_DIR / category / name
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True)
    
    run_id = setup_baseline(case_dir, custom_exp_data)
    
    metadata = METADATA_TEMPLATE.copy()
    metadata["description"] = description
    metadata["expected"] = expected
    metadata["run_id"] = run_id
    
    with open(case_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        
    if mutator_fn:
        mutator_fn(case_dir, run_id)

def main():
    if CORPUS_DIR.exists():
        shutil.rmtree(CORPUS_DIR)
        
    # VALID
    create_case(
        "valid", "baseline", "PASS", "Minimal successful execution without any tampering."
    )
    
    # FAIL CASES
    def mutate_ledger_hash(case_dir, run_id):
        ledger_file = case_dir / "ledger" / "ledger.jsonl"
        lines = []
        with open(ledger_file, "r") as f:
            for line in f:
                if line.strip(): lines.append(json.loads(line))
        lines[-1]["payload"]["receipt_hash"] = "0" * 64
        with open(ledger_file, "w") as f:
            for ev in lines:
                f.write(json.dumps(ev, separators=(',', ':'), sort_keys=True) + "\n")
                
    create_case(
        "fail", "ledger_hash_mutation", "FAIL", 
        "Ledger payload modified but ledger hash remains unchanged, causing hash verification failure.",
        mutate_ledger_hash
    )
    
    def mutate_receipt_field(case_dir, run_id):
        receipt_file = case_dir / "runs" / run_id / "receipt.json"
        with open(receipt_file, "r") as f: receipt = json.load(f)
        receipt["run_id"] = "RUN_TAMPERED"
        with open(receipt_file, "w") as f: json.dump(receipt, f)
        
    create_case(
        "fail", "receipt_field_tampered", "FAIL", 
        "Receipt run_id field modified, breaking the hash anchor to the ledger.",
        mutate_receipt_field
    )
    
    def mutate_input(case_dir, run_id):
        input_file = case_dir / "runs" / run_id / "inputs" / "config.json"
        with open(input_file, "w") as f: f.write('{"key": "tampered"}')
        
    create_case(
        "fail", "input_byte_mutation", "FAIL", 
        "Input file contents changed after freezing.",
        mutate_input
    )
    
    def mutate_undeclared_input(case_dir, run_id):
        input_file = case_dir / "runs" / run_id / "inputs" / "sneaky.txt"
        with open(input_file, "w") as f: f.write('sneaky')
        
    create_case(
        "fail", "undeclared_input_added", "FAIL", 
        "An undeclared file was added to the inputs directory.",
        mutate_undeclared_input
    )
    
    def mutate_input_size(case_dir, run_id):
        receipt_file = case_dir / "runs" / run_id / "receipt.json"
        with open(receipt_file, "r") as f: receipt = json.load(f)
        # Modify the declared size in the receipt, without changing the file hash
        # To make it fully canonical, we modify the receipt, then update the terminal event.
        if "config.json" in receipt.get("inputs", {}):
            receipt["inputs"]["config.json"]["size"] += 1
        new_receipt_hash = canonical_hash(receipt)
        with open(receipt_file, "w") as f: json.dump(receipt, f)
        
        ledger_file = case_dir / "ledger" / "ledger.jsonl"
        lines = []
        with open(ledger_file, "r") as f:
            for line in f:
                if line.strip(): lines.append(json.loads(line))
        lines[-1]["payload"]["receipt_hash"] = new_receipt_hash
        lines[-1]["hash"] = canonical_hash(lines[-1])
        with open(ledger_file, "w") as f:
            for ev in lines:
                f.write(json.dumps(ev, separators=(',', ':'), sort_keys=True) + "\n")

    create_case(
        "fail", "input_size_mutation", "FAIL", 
        "Declared input size was modified without altering the file hash.",
        mutate_input_size
    )
    
    # UNVERIFIABLE CASES
    def mutate_missing_receipt(case_dir, run_id):
        receipt_file = case_dir / "runs" / run_id / "receipt.json"
        receipt_file.unlink()
        
    create_case(
        "unverifiable", "missing_receipt", "UNVERIFIABLE", 
        "Receipt file was deleted.",
        mutate_missing_receipt
    )
    
    def mutate_orphaned_start(case_dir, run_id):
        ledger_file = case_dir / "ledger" / "ledger.jsonl"
        lines = []
        with open(ledger_file, "r") as f:
            for line in f:
                if line.strip(): lines.append(json.loads(line))
        lines.pop() # Remove RUN_COMPLETED
        with open(ledger_file, "w") as f:
            for ev in lines:
                f.write(json.dumps(ev, separators=(',', ':'), sort_keys=True) + "\n")
                
    def mutate_schema_violation(case_dir, run_id):
        receipt_file = case_dir / "runs" / run_id / "receipt.json"
        with open(receipt_file, "r") as f: receipt = json.load(f)
        # Violate schema by adding a float
        receipt["execution"]["exit_code"] = 1.5
        with open(receipt_file, "w") as f: json.dump(receipt, f)
        
    create_case(
        "fail", "schema_violation_float", "FAIL", 
        "Receipt exit_code mutated to a float, breaking schema validation.",
        mutate_schema_violation
    )
    
    def mutate_oversized_integer(case_dir, run_id):
        ledger_file = case_dir / "ledger" / "ledger.jsonl"
        lines = []
        with open(ledger_file, "r") as f:
            for line in f:
                if line.strip(): lines.append(json.loads(line))
                
        # Inject into RUN_STARTED payload (unconstrained)
        start_ev = lines[1]
        start_ev["payload"]["canonical_integer_edge"] = 9007199254740992
        # DO NOT update the hash, to prove canonicalizer rejects it directly
        
        with open(ledger_file, "w") as f:
            for ev in lines:
                f.write(json.dumps(ev, separators=(',', ':'), sort_keys=True) + "\n")

    create_case(
        "fail", "schema_violation_oversized_int", "FAIL", 
        "Ledger event payload contains an integer exceeding safe interoperable bounds. Schema validation passes, but canonical hashing must reject it.",
        mutate_oversized_integer
    )
    
    # CANONICAL JSON EDGES
    def mutate_canonical_json(case_dir, run_id):
        ledger_file = case_dir / "ledger" / "ledger.jsonl"
        lines = []
        with open(ledger_file, "r") as f:
            for line in f:
                if line.strip(): lines.append(json.loads(line))
                
        # Mutate the RUN_STARTED event (index 1)
        start_ev = lines[1]
        start_ev["payload"]["test_edge"] = {
            "z": [],
            "a": {},
            "b": "\\\"\b\f\n\r\t",
            "c": "こんにちは",
            "d": [3, 2, 1]
        }
        del start_ev["hash"]
        new_start_hash = canonical_hash(start_ev)
        start_ev["hash"] = new_start_hash
        
        # Propagate the hash chain down
        prev_hash = new_start_hash
        for i in range(2, len(lines)):
            lines[i]["previous_hash"] = prev_hash
            del lines[i]["hash"]
            # If it's the terminal event, we must ALSO update receipt_hash inside payload?
            # Wait, the receipt hash doesn't change because the receipt itself hasn't changed its payload YET.
            # But the receipt DOES contain `run_started_hash`. So we must mutate the receipt first.
            
        receipt_file = case_dir / "runs" / run_id / "receipt.json"
        with open(receipt_file, "r") as f: receipt = json.load(f)
        receipt["run_started_hash"] = new_start_hash
        new_receipt_hash = canonical_hash(receipt)
        with open(receipt_file, "w") as f: json.dump(receipt, f)
        
        # Now update the terminal event with the new receipt hash
        lines[-1]["payload"]["receipt_hash"] = new_receipt_hash
        
        # Now we can finish the chain hashing
        for i in range(2, len(lines)):
            lines[i]["hash"] = canonical_hash(lines[i])
            prev_hash = lines[i]["hash"]
            
        with open(ledger_file, "w") as f:
            for ev in lines:
                f.write(json.dumps(ev, separators=(',', ':'), sort_keys=True) + "\n")
                
    create_case(
        "valid", "canonical_json_edge", "PASS", 
        "Uses unicode, escapes, nested arrays, and empty objects in RUN_STARTED payload to test canonical serialization.",
        mutate_canonical_json
    )
    
    print(f"Corpus generated successfully at {CORPUS_DIR}")
    
    # Generate corpus manifest
    files_manifest = {}
    for p in CORPUS_DIR.rglob("*"):
        if p.is_file():
            rel_path = p.relative_to(CORPUS_DIR).as_posix()
            files_manifest[rel_path] = raw_hash_file(p)
            
    manifest = {
        "protocol_version": "0.1.0",
        "corpus_version": "0.1.0",
        "generator_version": "0.1.0",
        "files": files_manifest
    }
            
    manifest_path = Path("corpus") / "0.1.0_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest written to {manifest_path}")

if __name__ == "__main__":
    main()
