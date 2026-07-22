import os
import json
import hashlib
import time

SHADOW_DIR = r"D:\infinite\Infinity\Strategy\State\ShadowMode"
SHADOW_INPUTS = os.path.join(SHADOW_DIR, "shadow_inputs.jsonl")

def _hash_obj(obj):
    s = json.dumps(obj, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def write_shadow_envelope(cycle_id, raw_proposals, evaluated_proposals, state, metrics, ledger_data):
    try:
        os.makedirs(SHADOW_DIR, exist_ok=True)
        
        canonical_proposals = []
        for p in raw_proposals:
            canonical_proposals.append(json.loads(json.dumps(p)))
            
        capture_limitations = ["RAW_MODEL_RESPONSE_UNAVAILABLE"]
        
        # Pull independent authorization context from legacy data
        authorized_refs = ledger_data.get("authorized_source_refs", [])
        if not authorized_refs:
            capture_limitations.append("AUTHORIZED_SOURCE_CONTEXT_UNAVAILABLE")
            
        canonical_hash = _hash_obj(canonical_proposals)
        legacy_decision_hash = _hash_obj(evaluated_proposals)
        policy_hash = _hash_obj(ledger_data.get("trust_policy", {}))
        
        shadow_event_id = hashlib.sha256(
            f"{cycle_id}:{canonical_hash}:{legacy_decision_hash}:{policy_hash}:shadow_equivalence_v1".encode("utf-8")
        ).hexdigest()
        
        envelope = {
            "shadow_event_id": shadow_event_id,
            "cycle_id": cycle_id,
            "captured_utc": time.time(),
            "raw_llm_text": None,
            "capture_limitations": capture_limitations,
            "canonical_proposal": canonical_proposals,
            "canonical_proposal_hash": canonical_hash,
            "legacy_decision": evaluated_proposals,
            "legacy_decision_hash": legacy_decision_hash,
            "source_context": {
                "allowed_source_refs": sorted(list(set(authorized_refs)))
            },
            "planner_constraints": {"deadlock_risk": ledger_data.get("deadlock_risk_active", False)},
            "policy_id": ledger_data.get("trust_policy", {}).get("policy_id", "unknown"),
            "policy_hash": policy_hash,
            "comparison_policy_version": "shadow_equivalence_v1",
            "planner_version": "planner_v1",
            "gateway_version": "proposal_gateway_v1"
        }
        
        with open(SHADOW_INPUTS, "a", encoding="utf-8") as f:
            f.write(json.dumps(envelope) + "\n")
            f.flush()
    except Exception as e:
        # Minimal shadow-capture error path
        try:
            import traceback
            error_log = os.path.join(SHADOW_DIR, "shadow_capture_errors.log")
            error_item = {
                "timestamp": time.time(),
                "stage": "capture",
                "exception_type": type(e).__name__,
                "exception_hash": hashlib.sha256(traceback.format_exc().encode('utf-8')).hexdigest()[:16],
                "cycle_id": cycle_id
            }
            with open(error_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_item) + "\n")
        except:
            pass
