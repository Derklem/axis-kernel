import hashlib
import json
import uuid
from typing import Any, Dict

def generate_uuid() -> str:
    return str(uuid.uuid4())

SAFE_INTEGER_MIN = -9_007_199_254_740_991
SAFE_INTEGER_MAX = 9_007_199_254_740_991

def validate_canonical_numbers(obj: Any) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, float):
        raise ValueError("Floating-point numbers are prohibited in canonically hashed structures")
    if isinstance(obj, int):
        if not SAFE_INTEGER_MIN <= obj <= SAFE_INTEGER_MAX:
            raise ValueError("Integer outside safe interoperable bounds")
        return
    if isinstance(obj, dict):
        for v in obj.values():
            validate_canonical_numbers(v)
        return
    if isinstance(obj, list):
        for item in obj:
            validate_canonical_numbers(item)

def canonical_hash(data: Dict[str, Any]) -> str:
    """
    Canonical JSON hashing.
    Normalizes the dictionary by sorting keys and removing whitespace.
    Prohibits floating point numbers for cross-language determinism.
    Note: The 'hash' field is intentionally excluded from canonicalization by the caller.
    """
    validate_canonical_numbers(data)
    canonical_json = json.dumps(data, separators=(',', ':'), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
