import pytest
from strategy.evaluator import evaluate
from jsonschema import ValidationError
import copy
from strategy import EVALUATOR_VERSION

@pytest.fixture
def base_state():
    return {
        "state_schema_version": "1.1.0",
        "confidence": 95,
        "evidence_count": 100,
        "applied_observation_ids": []
    }

@pytest.fixture
def base_spec():
    return {
        "strategy_schema_version": "1.0.0",
        "decision_version": "strategy-hello-v1",
        "probe_threshold": 90,
        "minimum_evidence": 50
    }

@pytest.fixture
def base_obs():
    return {
        "observation_schema_version": "1.0.0",
        "observations": []
    }

def test_same_values_same_output(base_state, base_spec, base_obs):
    result1 = evaluate(base_state, base_spec, base_obs)
    result2 = evaluate(copy.deepcopy(base_state), copy.deepcopy(base_spec), copy.deepcopy(base_obs))
    
    assert result1 == result2
    
def test_reordered_object_keys_same_output(base_state, base_spec, base_obs):
    result1 = evaluate(base_state, base_spec, base_obs)
    
    # Reorder keys in state and spec
    state2 = {
        "evidence_count": 100,
        "applied_observation_ids": [],
        "confidence": 95,
        "state_schema_version": "1.1.0"
    }
    spec2 = {
        "minimum_evidence": 50,
        "probe_threshold": 90,
        "decision_version": "strategy-hello-v1",
        "strategy_schema_version": "1.0.0"
    }
    
    result2 = evaluate(state2, spec2, base_obs)
    assert result1 == result2

def test_one_changed_input_changed_input_root(base_state, base_spec, base_obs):
    result1 = evaluate(base_state, base_spec, base_obs)
    
    state2 = copy.deepcopy(base_state)
    state2["confidence"] = 96
    
    result2 = evaluate(state2, base_spec, base_obs)
    assert result1["input_root"] != result2["input_root"]

def test_input_dictionaries_remain_unmodified(base_state, base_spec, base_obs):
    s = copy.deepcopy(base_state)
    sp = copy.deepcopy(base_spec)
    o = copy.deepcopy(base_obs)
    
    evaluate(s, sp, o)
    
    assert s == base_state
    assert sp == base_spec
    assert o == base_obs

def test_confidence_failure_takes_precedence(base_state, base_spec, base_obs):
    # Both fail
    base_state["confidence"] = 80  # < 90
    base_state["evidence_count"] = 40 # < 50
    
    result = evaluate(base_state, base_spec, base_obs)
    assert result["decision"] == "PROBE"
    assert result["reason_code"] == "INSUFFICIENT_CONFIDENCE"

def test_evidence_failure_works_independently(base_state, base_spec, base_obs):
    base_state["confidence"] = 95 # >= 90
    base_state["evidence_count"] = 40 # < 50
    
    result = evaluate(base_state, base_spec, base_obs)
    assert result["decision"] == "PROBE"
    assert result["reason_code"] == "INSUFFICIENT_EVIDENCE"

def test_hold_branch_works(base_state, base_spec, base_obs):
    result = evaluate(base_state, base_spec, base_obs)
    assert result["decision"] == "HOLD"
    assert result["reason_code"] == "THRESHOLDS_SATISFIED"

def test_invalid_schema_rejected(base_state, base_spec, base_obs):
    base_state["extra"] = "field"
    with pytest.raises(ValidationError):
        evaluate(base_state, base_spec, base_obs)

def test_float_rejected(base_state, base_spec, base_obs):
    base_state["confidence"] = 95.5
    with pytest.raises(ValidationError):
        evaluate(base_state, base_spec, base_obs)

def test_oversized_integer_rejected(base_state, base_spec, base_obs):
    base_state["evidence_count"] = 9007199254740992
    with pytest.raises(ValidationError):
        evaluate(base_state, base_spec, base_obs)

def test_observations_bound_even_if_unused(base_state, base_spec, base_obs):
    result_a = evaluate(base_state, base_spec, base_obs)
    
    obs_b = copy.deepcopy(base_obs)
    obs_b["observations"].append({
        "observation_id": "OBS_00000000000000000000000000000000",
        "subject": "strategy-hello-v1",
        "support": 1,
        "reason_code": "EVALUATION_SUPPORTED",
        "source": {
            "run_id": "RUN_00000000-0000-0000-0000-000000000000",
            "receipt_hash": "0" * 64,
            "artifact_path": "artifacts/evaluation.json",
            "artifact_hash": "0" * 64
        }
    })
    result_b = evaluate(base_state, base_spec, obs_b)
    
    assert result_a["decision"] == result_b["decision"]
    assert result_a["input_root"] != result_b["input_root"]

def test_evaluator_version_and_decision_version(base_state, base_spec, base_obs):
    result = evaluate(base_state, base_spec, base_obs)
    assert result["evaluator_version"] == EVALUATOR_VERSION
    assert result["decision_version"] == "strategy-hello-v1"
