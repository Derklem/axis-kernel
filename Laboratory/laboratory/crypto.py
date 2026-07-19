import hashlib
import json
import uuid
from typing import Any, Dict

def generate_uuid() -> str:
    return str(uuid.uuid4())

def check_no_floats(obj: Any) -> None:
    if isinstance(obj, float):
        raise ValueError("Floating point numbers are prohibited in canonically hashed structures")
    elif isinstance(obj, dict):
        for v in obj.values():
            check_no_floats(v)
    elif isinstance(obj, list):
        for item in obj:
            check_no_floats(item)

def canonical_hash(data: Dict[str, Any]) -> str:
    """
    Canonical JSON hashing.
    Normalizes the dictionary by sorting keys and removing whitespace.
    Prohibits floating point numbers for cross-language determinism.
    Note: The 'hash' field is intentionally excluded from canonicalization by the caller.
    """
    check_no_floats(data)
    canonical_json = json.dumps(data, separators=(',', ':'), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
