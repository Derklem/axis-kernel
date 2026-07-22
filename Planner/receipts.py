import hashlib
import json

def generate_candidate_hash(candidate: dict) -> str:
    """Generates a stable SHA-256 hash of a normalized candidate dict."""
    canonical_json = json.dumps(candidate, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

def build_decision_receipt(candidate: dict, status: str, reasons: list[str], policy_hash: str, timestamp_utc: float) -> dict:
    """
    Constructs an immutable audit trail receipt for a processed candidate.
    """
    return {
        "candidate_id": candidate.get("candidate_id", "UNKNOWN"),
        "candidate_hash": generate_candidate_hash(candidate),
        "status": status,
        "reasons": reasons,
        "policy_hash": policy_hash,
        "timestamp_utc": timestamp_utc
    }
