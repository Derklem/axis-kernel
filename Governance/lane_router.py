import os
import json
import time
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
REGISTRY_FILE = os.path.join(ROOT, "Governance", "lane_registry.json")
WITNESS_ADMISSION_QUEUE = os.path.join(ROOT, "Governance", "Witness_Admission_Queue.jsonl")
CONVERSATIONAL_INBOX = os.path.join(ROOT, "Communication", "Conversational_Inbox.jsonl")

class GovernanceRejection(Exception):
    def __init__(self, message, original_file, supplied_class, allowed_class):
        super().__init__(message)
        self.original_file = original_file
        self.supplied_class = supplied_class
        self.allowed_class = allowed_class
        self.timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def to_dict(self):
        return {
            "reason": str(self),
            "source_file": self.original_file,
            "supplied_classification": self.supplied_class,
            "allowed_classifications": self.allowed_class,
            "timestamp_utc": self.timestamp_utc
        }

def route_payload(payload, source_filename):
    classification = payload.get("classification")
    
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            registry = json.load(f)
    except Exception as e:
        raise Exception(f"Failed to load lane registry: {e}")
        
    allowed_classifications = list(registry.get("classifications", {}).keys())

    if not classification:
        raise GovernanceRejection(
            "Missing classification. Explicit classification required.",
            source_filename,
            "None",
            allowed_classifications
        )

    lane = registry.get("classifications", {}).get(classification)
    if not lane:
        raise GovernanceRejection(
            f"Unknown classification: '{classification}'.",
            source_filename,
            classification,
            allowed_classifications
        )
        
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bridge_id = f"chat-{int(time.time() * 1000)}"
    
    question = payload.get("question", "")
    source = payload.get("source", "USER")
    original_ts = payload.get("timestamp_utc", now_utc)

    if lane == "witnessed":
        transformed = {
            "id": bridge_id,
            "content": f"Entity: {source}\nClaim: {question}",
            "status": "PENDING",
            "received_utc": original_ts,
            "bridged_utc": now_utc,
            "source_file": source_filename,
            "bridge_target": "Witness_Admission_Queue.jsonl",
            "classification": classification,
            "source": source,
            "rationale": payload.get("rationale"),
            "operator_ack": payload.get("operator_ack"),
            "epistemic_cost_ack": payload.get("epistemic_cost_ack")
        }
        target_path = WITNESS_ADMISSION_QUEUE
    elif lane == "conversational":
        transformed = {
            "id": bridge_id,
            "content": f"Entity: {source}\nMessage: {question}",
            "status": "PENDING",
            "received_utc": original_ts,
            "bridged_utc": now_utc,
            "source_file": source_filename,
            "bridge_target": "Conversational_Inbox.jsonl",
            "classification": classification
        }
        target_path = CONVERSATIONAL_INBOX
    else:
        raise Exception(f"Unknown lane '{lane}' in registry.")

    # Write
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(transformed) + "\n")
        
    return lane, target_path
