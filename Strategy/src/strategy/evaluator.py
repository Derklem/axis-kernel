import json
from importlib.resources import files
from jsonschema import validate
from laboratory.crypto import canonical_hash
from strategy import EVALUATOR_VERSION

def load_schema(package, name):
    schema_text = files(f"{package}.schemas").joinpath(name).read_text(encoding="utf-8")
    return json.loads(schema_text)

def evaluate(state: dict, strategy_spec: dict, observations: dict) -> dict:
    validate(instance=state, schema=load_schema("state", "state_vector.json"))
    validate(instance=strategy_spec, schema=load_schema("strategy", "strategy_spec.json"))
    validate(instance=observations, schema=load_schema("observation", "observation_feed.json"))
    
    input_envelope = {
        "state": state,
        "strategy_spec": strategy_spec,
        "observations": observations,
    }
    input_root = canonical_hash(input_envelope)
    
    if state["confidence"] < strategy_spec["probe_threshold"]:
        decision = "PROBE"
        reason = "INSUFFICIENT_CONFIDENCE"
    elif state["evidence_count"] < strategy_spec["minimum_evidence"]:
        decision = "PROBE"
        reason = "INSUFFICIENT_EVIDENCE"
    else:
        decision = "HOLD"
        reason = "THRESHOLDS_SATISFIED"
        
    result = {
        "decision_schema_version": "1.0.0",
        "decision_version": strategy_spec["decision_version"],
        "evaluator_version": EVALUATOR_VERSION,
        "decision": decision,
        "reason_code": reason,
        "input_root": input_root
    }
    
    validate(instance=result, schema=load_schema("strategy", "decision.json"))
    return result
