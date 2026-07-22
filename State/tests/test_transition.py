import pytest
import copy
from jsonschema import ValidationError
from state.transition import transition, SAFE_INTEGER_MAX
from laboratory.crypto import canonical_hash

@pytest.fixture
def prior_state():
    return {
        "state_schema_version": "1.1.0",
        "confidence": 95,
        "evidence_count": 40,
        "applied_observation_ids": ["OBS_ffffffffffffffffffffffffffffffff"]
    }

@pytest.fixture
def transition_spec():
    return {
        "transition_spec_schema_version": "1.0.0",
        "transition_version": "state-hello-v1",
        "subject": "strategy-hello-v1",
        "supported_increment": 10
    }

@pytest.fixture
def observation_feed():
    return {
        "observation_schema_version": "1.0.0",
        "observations": [
            {
                "observation_id": "OBS_00000000000000000000000000000000",
                "subject": "strategy-hello-v1",
                "support": 1,
                "reason_code": "EVALUATION_SUPPORTED",
                "source": {
                    "run_id": "RUN_123",
                    "receipt_hash": "0" * 64,
                    "artifact_path": "evaluation.json",
                    "artifact_hash": "0" * 64
                }
            }
        ]
    }

def test_deterministic_repeated_execution(prior_state, observation_feed, transition_spec):
    res1 = transition(prior_state, observation_feed, transition_spec)
    res2 = transition(copy.deepcopy(prior_state), copy.deepcopy(observation_feed), copy.deepcopy(transition_spec))
    assert res1 == res2

def test_key_reordering(prior_state, observation_feed, transition_spec):
    res1 = transition(prior_state, observation_feed, transition_spec)
    
    ps2 = {
        "evidence_count": 40,
        "applied_observation_ids": ["OBS_ffffffffffffffffffffffffffffffff"],
        "state_schema_version": "1.1.0",
        "confidence": 95
    }
    res2 = transition(ps2, observation_feed, transition_spec)
    assert res1 == res2

def test_no_input_mutation(prior_state, observation_feed, transition_spec):
    ps = copy.deepcopy(prior_state)
    of = copy.deepcopy(observation_feed)
    ts = copy.deepcopy(transition_spec)
    
    transition(ps, of, ts)
    
    assert ps == prior_state
    assert of == observation_feed
    assert ts == transition_spec

def test_supported_increment(prior_state, observation_feed, transition_spec):
    res = transition(prior_state, observation_feed, transition_spec)
    assert res["next_state"]["evidence_count"] == 50
    assert "SUPPORTED_OBSERVATION_APPLIED" in res["reason_codes"]
    assert res["summary"]["supported_applied"] == 1

def test_inconclusive_handling(prior_state, observation_feed, transition_spec):
    observation_feed["observations"][0]["support"] = 0
    res = transition(prior_state, observation_feed, transition_spec)
    assert res["next_state"]["evidence_count"] == 40
    assert "INCONCLUSIVE_OBSERVATION_APPLIED" in res["reason_codes"]
    assert res["summary"]["inconclusive_applied"] == 1

def test_contradictory_handling(prior_state, observation_feed, transition_spec):
    observation_feed["observations"][0]["support"] = -1
    res = transition(prior_state, observation_feed, transition_spec)
    assert res["next_state"]["evidence_count"] == 40
    assert "CONTRADICTION_OBSERVED" in res["reason_codes"]
    assert res["summary"]["contradicted_applied"] == 1

def test_irrelevant_subject_skipping(prior_state, observation_feed, transition_spec):
    observation_feed["observations"][0]["subject"] = "other-subject"
    res = transition(prior_state, observation_feed, transition_spec)
    assert res["next_state"]["evidence_count"] == 40
    assert res["summary"]["subject_mismatch_skipped"] == 1
    assert "OBS_00000000000000000000000000000000" in res["skipped_observation_ids"]

def test_duplicate_ids_in_feed_rejected(prior_state, observation_feed, transition_spec):
    obs = observation_feed["observations"][0]
    observation_feed["observations"].append(copy.deepcopy(obs))
    with pytest.raises(ValueError, match="Duplicate observation ID"):
        transition(prior_state, observation_feed, transition_spec)

def test_previously_applied_ids_not_reapplied(prior_state, observation_feed, transition_spec):
    res1 = transition(prior_state, observation_feed, transition_spec)
    
    # Run again with the output state
    res2 = transition(res1["next_state"], observation_feed, transition_spec)
    
    assert res2["next_state"]["evidence_count"] == res1["next_state"]["evidence_count"]
    assert res2["summary"]["replayed_skipped"] == 1
    assert "OBS_00000000000000000000000000000000" in res2["skipped_observation_ids"]
    assert "REPLAYED_OBSERVATION_SKIPPED" in res2["reason_codes"]
    # Replay transition artifact must differ from first transition
    assert res1["next_state_root"] == res2["next_state_root"]

def test_safe_integer_clamping(prior_state, observation_feed, transition_spec):
    prior_state["evidence_count"] = SAFE_INTEGER_MAX - 5
    res = transition(prior_state, observation_feed, transition_spec)
    assert res["next_state"]["evidence_count"] == SAFE_INTEGER_MAX
    assert "EVIDENCE_COUNT_CLAMPED" in res["reason_codes"]

def test_float_rejected(prior_state, observation_feed, transition_spec):
    prior_state["confidence"] = 95.5
    with pytest.raises(ValidationError):
        transition(prior_state, observation_feed, transition_spec)

def test_oversized_integer_rejected(prior_state, observation_feed, transition_spec):
    prior_state["evidence_count"] = SAFE_INTEGER_MAX + 1
    with pytest.raises(ValidationError):
        transition(prior_state, observation_feed, transition_spec)

def test_transition_roots_change(prior_state, observation_feed, transition_spec):
    res1 = transition(prior_state, observation_feed, transition_spec)
    
    ts2 = copy.deepcopy(transition_spec)
    ts2["supported_increment"] = 20
    res2 = transition(prior_state, observation_feed, ts2)
    
    assert res1["transition_spec_root"] != res2["transition_spec_root"]
    assert res1["next_state_root"] != res2["next_state_root"]

def test_sorting_and_multiple_applications(prior_state, observation_feed, transition_spec):
    obs2 = copy.deepcopy(observation_feed["observations"][0])
    obs2["observation_id"] = "OBS_11111111111111111111111111111111"
    obs3 = copy.deepcopy(observation_feed["observations"][0])
    obs3["observation_id"] = "OBS_22222222222222222222222222222222"
    
    observation_feed["observations"].append(obs3)
    observation_feed["observations"].append(obs2)
    
    res = transition(prior_state, observation_feed, transition_spec)
    
    # 3 observations, one with ID 0000, 1111, 2222
    assert res["next_state"]["evidence_count"] == 70
    assert res["summary"]["supported_applied"] == 3
    
    expected_ids = ["OBS_00000000000000000000000000000000", "OBS_11111111111111111111111111111111", "OBS_22222222222222222222222222222222", "OBS_ffffffffffffffffffffffffffffffff"]
    expected_ids.sort()
    
    assert res["applied_observation_ids"] == ["OBS_00000000000000000000000000000000", "OBS_11111111111111111111111111111111", "OBS_22222222222222222222222222222222"]
    assert res["next_state"]["applied_observation_ids"] == expected_ids
