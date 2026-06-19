import os
import json
import hashlib

def parse_ledger_fast(ledger_path):
    """
    Parses the receptor ledger quickly, enforcing cryptographic continuity, 
    but without validating physical reality (no disk reads of target files).
    
    Returns:
        cases (dict): Mapped by case_id containing events and payloads.
        metrics (dict): High-level system health metrics.
        receipts (list): The raw ordered receipt list.
    """
    if not os.path.exists(ledger_path):
        return {}, {"session_burden": 0.0, "accepted": 0, "quarantined": 0, "overrides": 0, "audit_requests": 0}, []

    cases = {}
    receipts = []
    expected_parent = "GENESIS"
    
    metrics = {
        "session_burden": 0.0,
        "accepted": 0,
        "quarantined": 0,
        "overrides": 0,
        "audit_requests": 0
    }

    with open(ledger_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            
            receipt = json.loads(line)
            receipts.append(receipt)
            case_id = receipt.get("case_id")
            event_type = receipt["event_type"]

            # Cryptographic continuity check
            if receipt["parent_receptor_head"] != expected_parent:
                raise ValueError(f"Chain broken at receipt {idx}: Expected parent {expected_parent}, got {receipt['parent_receptor_head']}")
            
            payload_bytes = json.dumps(receipt["payload"], sort_keys=True, separators=(",", ":")).encode("utf-8")
            computed_payload_hash = hashlib.sha256(payload_bytes).hexdigest()
            if computed_payload_hash != receipt["payload_hash"]:
                raise ValueError(f"Payload hash mismatch at receipt {idx}")

            receipt_base = f"{receipt['event_type']}|{receipt['case_id']}|{receipt['parent_receptor_head']}|{computed_payload_hash}|{receipt['timestamp']}"
            computed_receipt_hash = hashlib.sha256(receipt_base.encode("utf-8")).hexdigest()
            if computed_receipt_hash != receipt["receipt_hash"]:
                raise ValueError(f"Receipt hash mismatch at receipt {idx}")
                
            expected_parent = computed_receipt_hash

            if case_id:
                if case_id not in cases:
                    cases[case_id] = {"events": [], "evidence": None, "observation": None}
                
                case = cases[case_id]
                case["events"].append(event_type)
                case.setdefault("payloads", {})[event_type] = receipt.get("payload", {})

                if event_type in ["RECEPTOR_OBSERVATION_RECORDED", "RECEPTOR_DIFF_OBSERVED"]:
                    case["observation"] = receipt["payload"]
                elif event_type == "RECEPTOR_DELTA_ACCEPTED":
                    metrics["accepted"] += 1
                elif event_type == "RECEPTOR_DELTA_QUARANTINED":
                    metrics["quarantined"] += 1
                elif event_type == "ADJUDICATION_RULING":
                    metrics["overrides"] += 1
                elif event_type == "AUDITOR_REVIEW_REQUESTED":
                    metrics["audit_requests"] += 1
                elif event_type == "RECEPTOR_GOVERNANCE_EVALUATED":
                    burdens = receipt["payload"].get("burdens", {})
                    metrics["session_burden"] += sum(burdens.values())
                elif event_type == "RECOVERY_REHEARSED":
                    patch_path = receipt["payload"].get("recovery_patch_path")
                    # Reset case struct but retain payload parsing
                    cases[case_id] = {"events": [event_type], "patch_path": patch_path, "payloads": {event_type: receipt.get("payload", {})}}

    return cases, metrics, receipts
