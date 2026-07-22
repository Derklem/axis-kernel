import os
import json
import uuid
import datetime
import F8_1_Market_Dynamics_Engine as engine

INTAKE_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_external_intake.jsonl"
QUARANTINE_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_quarantine.jsonl"
CRITIQUES_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_external_critiques.jsonl"
REJECTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_intake_rejections.jsonl"

def append_jsonl(path, data):
    with open(path, 'a') as f:
        f.write(json.dumps(data) + "\n")

def process_intake(payload):
    # 1. Generate core intake metadata
    intake_id = payload.get('intake_id', f"EXT-{uuid.uuid4().hex[:8].upper()}")
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
    
    intake_record = {
        "intake_id": intake_id,
        "source_entity": payload.get('source_entity', 'unknown'),
        "artifact_hash": payload.get('artifact_hash'),
        "timestamp_utc": ts,
        "lane": "unknown"
    }
    
    # 2. Schema Validation
    if not payload.get('source_entity'):
        return reject_intake(intake_record, payload, "Missing source_entity")
        
    has_claims = isinstance(payload.get('claims'), list)
    has_raw = isinstance(payload.get('raw_payload'), str) and payload['raw_payload'].strip()
    
    if has_claims:
        intake_record['lane'] = "A_STRUCTURED"
        append_jsonl(INTAKE_PATH, intake_record)
        return process_lane_a(intake_id, payload['claims'])
        
    elif has_raw:
        intake_record['lane'] = "B_NARRATIVE"
        append_jsonl(INTAKE_PATH, intake_record)
        return process_lane_b(intake_id, payload)
        
    else:
        return reject_intake(intake_record, payload, "Payload must contain either 'claims' array or 'raw_payload' string")

def reject_intake(record, raw_payload, reason):
    rejection = {
        **record,
        "raw_payload_excerpt": str(raw_payload)[:500],
        "rejection_reason": reason
    }
    append_jsonl(REJECTIONS_PATH, rejection)
    return {"status": "REJECTED", "reason": reason}

def process_lane_b(intake_id, payload):
    critique = {
        "critique_id": f"CRIT-{uuid.uuid4().hex[:8].upper()}",
        "intake_id": intake_id,
        "source_entity": payload['source_entity'],
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "raw_payload": payload['raw_payload'],
        "admissibility_status": "CRITIQUE_ONLY"
    }
    append_jsonl(CRITIQUES_PATH, critique)
    return {"status": "CRITIQUE_LOGGED", "critique_id": critique["critique_id"]}

def process_lane_a(intake_id, claims):
    results = []
    for c in claims:
        claim_id = c.get('claim_id', f"CLAIM-{uuid.uuid4().hex[:8].upper()}")
        
        # Validate required claim schema
        required = ['claim_text', 'claim_type', 'independence_classification', 'theory_group_id', 'supports_theory_id']
        missing = [k for k in required if not c.get(k)]
        if missing:
            quarantine_claim(intake_id, claim_id, c, f"Missing required fields: {missing}")
            results.append({"claim_id": claim_id, "status": "QUARANTINED", "reason": "Schema incomplete"})
            continue
            
        ctype = c['claim_type']
        iclass = c['independence_classification']
        
        # Admissibility rule
        is_admissible = ctype == "observation" and iclass in ["primary", "artifact_backed"]
        
        if not is_admissible:
            quarantine_claim(intake_id, claim_id, c, f"Inadmissible classification: {ctype} + {iclass}")
            results.append({"claim_id": claim_id, "status": "QUARANTINED", "reason": "Failed admissibility rules"})
            continue
            
        # Admissible -> Route to F8 Market
        obs = {
            "theory_group_id": c['theory_group_id'],
            "supports_theory_id": c['supports_theory_id'],
            "evidence_weight": c.get('evidence_weight', 1.0),
            "reason": c['claim_text'],
            "is_drill": False,
            "source": "external_intake_gateway",
            "provenance": {
                "type": "intake_artifact",
                "ref": intake_id,
                "claim_id": claim_id,
                "original_source": c.get('original_source')
            }
        }
        
        # Ensure F8 engine has an authenticated wrapper if it expects one
        market_result = engine.append_observation(obs)
        if market_result.get("rejection_reason"):
            results.append({"claim_id": claim_id, "status": "MARKET_REJECTED", "reason": market_result["rejection_reason"]})
        else:
            results.append({"claim_id": claim_id, "status": "MARKET_ACCEPTED", "event_id": market_result.get("event_id")})
            
    return {"status": "PROCESSED", "results": results}

def quarantine_claim(intake_id, claim_id, claim_payload, reason):
    q = {
        "quarantine_id": f"QUAR-{uuid.uuid4().hex[:8].upper()}",
        "intake_id": intake_id,
        "claim_id": claim_id,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "claim_payload": claim_payload,
        "quarantine_reason": reason,
        "admissibility_status": "QUARANTINED"
    }
    append_jsonl(QUARANTINE_PATH, q)
