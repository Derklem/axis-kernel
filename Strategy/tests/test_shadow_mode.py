import os
import json
import time
import hashlib
import sys
import shutil
import pytest

sys.path.append(r"D:\infinite\Infinity")

from Strategy import shadow_mode
from Strategy import process_shadow_queue

TEST_DIR = os.path.join(os.path.dirname(__file__), "test_shadow_data")

@pytest.fixture
def temp_shadow_dir():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR, exist_ok=True)
    
    orig_shadow_dir = shadow_mode.SHADOW_DIR
    orig_shadow_inputs = shadow_mode.SHADOW_INPUTS
    orig_worker_inputs = process_shadow_queue.SHADOW_INPUTS
    orig_worker_results = process_shadow_queue.SHADOW_RESULTS
    orig_worker_errors = process_shadow_queue.SHADOW_ERRORS
    
    shadow_mode.SHADOW_DIR = TEST_DIR
    shadow_mode.SHADOW_INPUTS = os.path.join(TEST_DIR, "shadow_inputs.jsonl")
    process_shadow_queue.SHADOW_INPUTS = os.path.join(TEST_DIR, "shadow_inputs.jsonl")
    process_shadow_queue.SHADOW_RESULTS = os.path.join(TEST_DIR, "shadow_results.jsonl")
    process_shadow_queue.SHADOW_ERRORS = os.path.join(TEST_DIR, "shadow_errors.jsonl")
    
    yield TEST_DIR
    
    shadow_mode.SHADOW_DIR = orig_shadow_dir
    shadow_mode.SHADOW_INPUTS = orig_shadow_inputs
    process_shadow_queue.SHADOW_INPUTS = orig_worker_inputs
    process_shadow_queue.SHADOW_RESULTS = orig_worker_results
    process_shadow_queue.SHADOW_ERRORS = orig_worker_errors
    
    shutil.rmtree(TEST_DIR)

def create_mock_envelope(scenario):
    # Base minimal proposal
    base_proposal = {
        "candidate_id": f"CAND_{scenario}",
        "title": f"Test {scenario}",
        "objective": "Test objective",
        "expected_information_gain": 0.5,
        "epistemic_debt_age_hours": 24,
        "estimated_compute_minutes": 10,
        "attention_cost": "LOW",
        "risk_level": "GREEN",
        "execution_mode": "autonomous",
        "status": "candidate",
        "dependencies": [],
        "constraints": [],
        "source_refs": ["REF_1"]
    }
    
    proposals = []
    
    if scenario == "accepted_clean":
        proposals.append(base_proposal)
    elif scenario == "accepted_repair":
        p = dict(base_proposal)
        p["risk_level"] = "green" # Lowercase to force repair
        proposals.append(p)
    elif scenario == "missing_field":
        p = dict(base_proposal)
        del p["objective"]
        proposals.append(p)
    elif scenario == "unknown_field":
        p = dict(base_proposal)
        p["invalid_key"] = "value"
        proposals.append(p)
    elif scenario == "unauthorized_source":
        p = dict(base_proposal)
        p["source_refs"] = ["UNAUTHORIZED"]
        proposals.append(p)
    elif scenario == "empty_batch":
        pass
    elif scenario == "mixed_batch":
        proposals.append(base_proposal)
        p_missing = dict(base_proposal)
        p_missing["candidate_id"] = "CAND_MIXED_MISSING"
        del p_missing["objective"]
        proposals.append(p_missing)
    elif scenario == "legacy_match":
        proposals.append(base_proposal)
    elif scenario == "legacy_differ":
        proposals.append(base_proposal)
    
    legacy_decision = []
    if scenario in ("legacy_match", "legacy_differ", "accepted_clean", "accepted_repair"):
        legacy_decision.append({
            "candidate_id": base_proposal["candidate_id"],
            "evaluation": {"solver_accepted": True}
        })
        
    if scenario == "legacy_differ":
        # Legacy executed a DIFFERENT proposal
        legacy_decision = [{
            "candidate_id": "CAND_SOME_OTHER",
            "evaluation": {"solver_accepted": True}
        }]
        
    env = {
        "shadow_event_id": f"EVENT_{scenario}",
        "cycle_id": 1,
        "captured_utc": time.time(),
        "canonical_proposal": proposals,
        "legacy_decision": legacy_decision,
        "source_context": {
            "allowed_source_refs": ["REF_1"],
            "ecosystem_summary": {}
        },
        "policy_id": "mock_policy"
    }
    return env

def test_shadow_queue_matrix(temp_shadow_dir):
    scenarios = [
        "accepted_clean",
        "accepted_repair",
        "missing_field",
        "unknown_field",
        "unauthorized_source",
        "empty_batch",
        "mixed_batch",
        "legacy_match",
        "legacy_differ",
        "legacy_match" # Duplicate replay
    ]
    
    # Write inputs
    for s in scenarios:
        env = create_mock_envelope(s)
        process_shadow_queue.write_jsonl(process_shadow_queue.SHADOW_INPUTS, env)
        
    # Process queue
    process_shadow_queue.main()
    
    # Read results
    results = []
    if os.path.exists(process_shadow_queue.SHADOW_RESULTS):
        with open(process_shadow_queue.SHADOW_RESULTS, "r") as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
                    
    errors = []
    if os.path.exists(process_shadow_queue.SHADOW_ERRORS):
        with open(process_shadow_queue.SHADOW_ERRORS, "r") as f:
            for line in f:
                if line.strip():
                    errors.append(json.loads(line))
                    
    # Verify no errors
    assert len(errors) == 0, f"Found errors: {errors}"
    
    # Verify exact number of unique terminal results (9 unique events)
    assert len(results) == 9, f"Expected 9 unique results, got {len(results)}"
    
    # Verify duplicate replay is skipped
    # Run again to ensure idempotency
    process_shadow_queue.main()
    results_second = []
    with open(process_shadow_queue.SHADOW_RESULTS, "r") as f:
        for line in f:
            if line.strip():
                results_second.append(json.loads(line))
    
    assert len(results_second) == 9, "Idempotency failed, processed duplicates"
    
    # Validate specific scenarios
    res_map = {r["shadow_event_id"]: r for r in results}
    
    # 1. accepted_clean
    r = res_map["EVENT_accepted_clean"]
    assert r["gateway_batch_status"] == "ALL_ACCEPTED"
    assert r["gateway_repairs"] == 0
    assert r["planner_status"] == "AGENDA_BUILT"
    
    # 2. accepted_repair
    r = res_map["EVENT_accepted_repair"]
    assert r["gateway_batch_status"] == "ALL_ACCEPTED"
    assert r["gateway_repairs"] > 0
    
    # 3. missing_field
    r = res_map["EVENT_missing_field"]
    assert r["gateway_batch_status"] == "NO_ACCEPTED_CANDIDATES"
    assert r["gateway_status_counts"]["NEEDS_REVISION"] == 1
    
    # 4. unknown_field
    r = res_map["EVENT_unknown_field"]
    assert r["gateway_batch_status"] == "NO_ACCEPTED_CANDIDATES"
    assert r["gateway_status_counts"]["NEEDS_REVISION"] == 1
    
    # 5. unauthorized_source
    r = res_map["EVENT_unauthorized_source"]
    assert r["gateway_batch_status"] == "NO_ACCEPTED_CANDIDATES"
    assert r["gateway_status_counts"]["REJECTED"] == 1
    
    # 6. empty_batch
    r = res_map["EVENT_empty_batch"]
    assert r["planner_status"] == "NO_ACCEPTED_CANDIDATES"
    
    # 7. mixed_batch
    r = res_map["EVENT_mixed_batch"]
    assert r["gateway_batch_status"] == "PARTIAL_ACCEPTANCE"
    
    # 8. legacy_match
    r = res_map["EVENT_legacy_match"]
    assert r["equivalence_class"] == "exact_match"
    
    # 9. legacy_differ
    r = res_map["EVENT_legacy_differ"]
    assert r["equivalence_class"] == "material_disagreement"

def test_frozen_envelope_replay_is_deterministic(temp_shadow_dir):
    import copy
    env = create_mock_envelope("accepted_clean")
    
    # Process twice in memory to verify deterministic properties
    result_a = process_shadow_queue.process_envelope(copy.deepcopy(env))
    # Slight sleep or modification of time context
    time.sleep(0.01)
    result_b = process_shadow_queue.process_envelope(copy.deepcopy(env))
    
    assert result_a["deterministic_result_hash"] == result_b["deterministic_result_hash"], "Result hash varies on frozen envelope replay"
    
    # Verify latencies are not in the hash and can differ
    assert "gateway_latency_ms" in result_a
    assert "total_latency_ms" in result_b
    assert "deterministic_result_hash" in result_a

if __name__ == "__main__":
    pytest.main([__file__])
