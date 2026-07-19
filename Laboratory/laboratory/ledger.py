import json
import time
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from laboratory.crypto import generate_uuid, canonical_hash

PROTOCOL_VERSION = "0.1.0"
LABORATORY_VERSION = "0.1.0"
RECEIPT_SCHEMA_VERSION = "1.0.0"
EVENT_SCHEMA_VERSION = "1.0.0"

def get_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def get_ledger_file(ledger_dir: Path) -> Path:
    return ledger_dir / "ledger.jsonl"

class LedgerLock:
    def __init__(self, ledger_dir: Path, timeout_seconds: int = 10):
        self.lock_path = ledger_dir / ".ledger.lock"
        self.timeout = timeout_seconds

    def __enter__(self):
        start_time = time.time()
        while True:
            try:
                self.lock_path.mkdir()
                # Write PID inside lock to identify owner
                pid_file = self.lock_path / "owner.pid"
                pid_file.write_text(str(os.getpid()))
                break
            except FileExistsError:
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Could not acquire ledger lock at {self.lock_path}. Is another process running? Delete if stale.")
                time.sleep(0.1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            pid_file = self.lock_path / "owner.pid"
            if pid_file.exists():
                pid_file.unlink()
            self.lock_path.rmdir()
        except OSError:
            pass

def validate_ledger_append(ledger_file: Path, new_sequence: int, previous_hash: str):
    """Verifies the last event in the ledger is sound before appending."""
    if not ledger_file.exists():
        return
        
    last_line = None
    with open(ledger_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last_line = line
                
    if not last_line:
        return
        
    try:
        last_event = json.loads(last_line)
    except json.JSONDecodeError:
        raise ValueError("Ledger tail is corrupted (invalid JSON).")
        
    if "sequence" not in last_event or "hash" not in last_event:
        raise ValueError("Ledger tail is corrupted (missing critical fields).")
        
    if last_event["sequence"] + 1 != new_sequence:
        raise ValueError(f"Sequence mismatch. Ledger has {last_event['sequence']}, attempted {new_sequence}.")
        
    if last_event["hash"] != previous_hash:
        raise ValueError("Hash chain mismatch.")
        
    # Recompute last event hash to ensure integrity
    expected_hash = last_event["hash"]
    test_event = last_event.copy()
    del test_event["hash"]
    if canonical_hash(test_event) != expected_hash:
        raise ValueError("Ledger tail hash integrity is broken.")

def init_ledger(ledger_dir: Path) -> str:
    if not ledger_dir.exists():
        ledger_dir.mkdir(parents=True, exist_ok=True)
        
    with LedgerLock(ledger_dir):
        ledger_file = get_ledger_file(ledger_dir)
        if ledger_file.exists():
            raise FileExistsError(f"Ledger already exists at {ledger_file}")
            
        genesis_payload = {
            "protocol_version": PROTOCOL_VERSION,
            "laboratory_version": LABORATORY_VERSION,
            "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
            "ledger_uuid": generate_uuid()
        }
        
        event = {
            "sequence": 0,
            "timestamp": get_utc_now(),
            "event_schema_version": EVENT_SCHEMA_VERSION,
            "event_type": "LEDGER_INITIALIZED",
            "payload": genesis_payload,
            "previous_hash": None
        }
        
        event_hash = canonical_hash(event)
        event["hash"] = event_hash
        
        with open(ledger_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(event, separators=(',', ':'), sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
            
    return event_hash

def get_last_event(ledger_dir: Path) -> Optional[Dict[str, Any]]:
    ledger_file = get_ledger_file(ledger_dir)
    if not ledger_file.exists():
        return None
        
    last_line = None
    with open(ledger_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last_line = line
                
    if last_line:
        return json.loads(last_line)
    return None

def append_event(ledger_dir: Path, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    ledger_file = get_ledger_file(ledger_dir)
    
    with LedgerLock(ledger_dir):
        if not ledger_file.exists():
            raise FileNotFoundError(f"No ledger found at {ledger_file}. Run lab init first.")
            
        last_event = get_last_event(ledger_dir)
        if not last_event:
            raise ValueError("Ledger is empty, missing genesis block.")
            
        sequence = last_event["sequence"] + 1
        previous_hash = last_event["hash"]
        
        # Validates the chain before mutating
        validate_ledger_append(ledger_file, sequence, previous_hash)
        
        event = {
            "sequence": sequence,
            "timestamp": get_utc_now(),
            "event_schema_version": EVENT_SCHEMA_VERSION,
            "event_type": event_type,
            "payload": payload,
            "previous_hash": previous_hash
        }
        
        event_hash = canonical_hash(event)
        event["hash"] = event_hash
        
        with open(ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, separators=(',', ':'), sort_keys=True) + "\n")
            f.flush()
            os.fsync(f.fileno())
            
    return event
