import json
import os
import subprocess
import sys
import copy
from pathlib import Path
from laboratory.crypto import canonical_hash
from jsonschema import validate
from jsonschema.exceptions import ValidationError
import tempfile
import shutil

repo_root = Path(__file__).parent.parent
if (repo_root / "Agenda" / "src").exists():
    for pkg in ["Agenda", "State", "Strategy", "Observation", "Laboratory"]:
        sys.path.insert(0, str(repo_root / pkg / "src"))

from agenda.planner import generate_agenda

def run_cli_agenda(planner_input, planner_spec):
    with open("input.json", "w") as f: json.dump(planner_input, f)
    with open("spec.json", "w") as f: json.dump(planner_spec, f)
    
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    
    res = subprocess.run([
        sys.executable, "-m", "agenda.cli",
        "--input", "input.json",
        "--spec", "spec.json",
        "--output", "agenda.json"
    ], capture_output=True, env=env)
    
    if res.returncode != 0:
        print("CLI FAILED:")
        print("STDOUT:", res.stdout.decode('utf-8'))
        print("STDERR:", res.stderr.decode('utf-8'))
        return None
    with open("agenda.json") as f:
        return json.load(f)

def test_api_cli_parity():
    print("--- Test: API vs CLI Parity ---")
    candidates = [
        {
            "candidate_id": "c1",
            "expected_information_gain": 100,
            "estimated_compute_cost": 10,
            "estimated_attention_cost": 5,
            "experiment_spec_root": "hash1"
        }
    ]
    planner_input = {
        "planner_input_schema_version": "1.0.0",
        "state_root": "dummy_state_root",
        "strategy_decision_root": "dummy_strategy_decision_root",
        "candidates": candidates
    }
    planner_spec = {
        "planner_spec_schema_version": "1.0.0",
        "gain_weight": 1, "compute_cost_weight": 1, "attention_cost_weight": 1,
        "max_agenda_items": 2, "max_compute_budget": 100, "max_attention_budget": 100
    }
    
    api_result = generate_agenda(planner_input, planner_spec)
    cli_result = run_cli_agenda(planner_input, planner_spec)
    
    if canonical_hash(api_result) != canonical_hash(cli_result):
        import pprint
        print("API RESULT:")
        pprint.pprint(api_result)
        print("CLI RESULT:")
        pprint.pprint(cli_result)
        
    assert canonical_hash(api_result) == canonical_hash(cli_result), "API and CLI output canonical hashes differ!"
    print("PASS: API and CLI produce identical artifacts.")

def test_version_vs_structural_mismatch():
    print("--- Test: Version vs Structural Mismatch ---")
    bad_structure = {
        "planner_input_schema_version": "1.0.0",
        "state_root": "dummy",
    }
    planner_spec = {
        "planner_spec_schema_version": "1.0.0",
        "gain_weight": 1, "compute_cost_weight": 1, "attention_cost_weight": 1,
        "max_agenda_items": 1, "max_compute_budget": 1, "max_attention_budget": 1
    }
    res = generate_agenda(bad_structure, planner_spec)
    assert res["status"] == "FAILED_INPUT_VALIDATION"
    
    bad_version = {
        "planner_input_schema_version": "2.0.0",
        "state_root": "dummy",
        "strategy_decision_root": "dummy",
        "candidates": []
    }
    res2 = generate_agenda(bad_version, planner_spec)
    assert res2["status"] == "FAILED_INPUT_VALIDATION"
    print("PASS: Version mismatch and Structural mismatch fail deterministically.")

def test_root_consistency():
    print("--- Test: Root Consistency ---")
    planner_input = {
        "planner_input_schema_version": "1.0.0",
        "state_root": "dummy_state",
        "strategy_decision_root": "dummy_strat",
        "candidates": []
    }
    planner_spec = {
        "planner_spec_schema_version": "1.0.0",
        "gain_weight": 1, "compute_cost_weight": 1, "attention_cost_weight": 1,
        "max_agenda_items": 1, "max_compute_budget": 1, "max_attention_budget": 1
    }
    agenda = generate_agenda(planner_input, planner_spec)
    assert agenda["planner_input_root"] == canonical_hash(planner_input)
    assert agenda["planner_spec_root"] == canonical_hash(planner_spec)
    print("PASS: Emitted roots match independently recomputed roots.")

def test_idempotence():
    print("--- Test: Idempotence Round-Trip ---")
    obj = {"a": 1, "b": "test", "c": [3, 2, 1], "d": {"z": 100, "y": 200}}
    root1 = canonical_hash(obj)
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    obj2 = json.loads(s)
    root2 = canonical_hash(obj2)
    assert root1 == root2, "Root changed after round trip!"
    print("PASS: Parse/serialize round-trip is strictly idempotent.")

def test_boundary_integers():
    print("--- Test: Boundary Integers ---")
    MAX_SAFE_INTEGER = 9007199254740991
    
    base_input = {
        "planner_input_schema_version": "1.0.0",
        "state_root": "0"*64, "strategy_decision_root": "0"*64,
        "candidates": [
            {
                "candidate_id": "c1",
                "expected_information_gain": MAX_SAFE_INTEGER,
                "estimated_compute_cost": 0,
                "estimated_attention_cost": 0,
                "experiment_spec_root": "0"*64
            }
        ]
    }
    spec = {
        "planner_spec_schema_version": "1.0.0",
        "gain_weight": 1, "compute_cost_weight": 1, "attention_cost_weight": 1,
        "max_agenda_items": 1, "max_compute_budget": 1, "max_attention_budget": 1
    }
    
    res = generate_agenda(base_input, spec)
    assert res["status"] == "SUCCESS", "Failed on exact max integer"
    
    base_input["candidates"][0]["expected_information_gain"] = MAX_SAFE_INTEGER - 1
    res = generate_agenda(base_input, spec)
    assert res["status"] == "SUCCESS", "Failed on max integer - 1"
    
    base_input["candidates"][0]["expected_information_gain"] = MAX_SAFE_INTEGER + 1
    res = generate_agenda(base_input, spec)
    assert res["status"] == "FAILED_INPUT_VALIDATION", "Did not fail on max integer + 1"
    
    print("PASS: Boundary integers handled safely by protocol.")

def test_multiple_concurrent_hypotheses():
    print("--- Test: Multiple Concurrent Hypotheses ---")
    candidates = []
    # Add 50 candidates, some with identical scores
    for i in range(50):
        candidates.append({
            "candidate_id": f"c_{i:03d}",
            "expected_information_gain": 100, # all same gain
            "estimated_compute_cost": 10,
            "estimated_attention_cost": 10,
            "experiment_spec_root": "0"*64
        })
    # Mix them up
    candidates = candidates[::-1]
    
    planner_input = {
        "planner_input_schema_version": "1.0.0",
        "state_root": "0"*64,
        "strategy_decision_root": "0"*64,
        "candidates": candidates
    }
    planner_spec = {
        "planner_spec_schema_version": "1.0.0",
        "gain_weight": 1, "compute_cost_weight": 1, "attention_cost_weight": 1,
        "max_agenda_items": 50, "max_compute_budget": 1000, "max_attention_budget": 1000
    }
    
    agenda = generate_agenda(planner_input, planner_spec)
    assert agenda["status"] == "SUCCESS"
    assert len(agenda["ranked_items"]) == 50
    # Check lexical tie-breaking
    for i in range(50):
        assert agenda["ranked_items"][i]["candidate_id"] == f"c_{i:03d}"
    print("PASS: Handled many hypotheses with strict lexical tie-breaking.")

def test_resource_constrained_agendas():
    print("--- Test: Resource Constrained Agendas ---")
    candidates = [
        {"candidate_id": "c_fits_exactly", "expected_information_gain": 200, "estimated_compute_cost": 10, "estimated_attention_cost": 5, "experiment_spec_root": "0"*64},
        {"candidate_id": "c_slightly_exceeds", "expected_information_gain": 100, "estimated_compute_cost": 1, "estimated_attention_cost": 1, "experiment_spec_root": "0"*64},
        {"candidate_id": "c_massively_exceeds", "expected_information_gain": 300, "estimated_compute_cost": 1000, "estimated_attention_cost": 1000, "experiment_spec_root": "0"*64}
    ]
    planner_input = {
        "planner_input_schema_version": "1.0.0",
        "state_root": "0"*64, "strategy_decision_root": "0"*64,
        "candidates": candidates
    }
    planner_spec = {
        "planner_spec_schema_version": "1.0.0",
        "gain_weight": 1, "compute_cost_weight": 1, "attention_cost_weight": 1,
        "max_agenda_items": 5, "max_compute_budget": 10, "max_attention_budget": 5
    }
    
    agenda = generate_agenda(planner_input, planner_spec)
    assert agenda["status"] == "SUCCESS"
    # c_massively_exceeds is REJECTED outright
    assert len(agenda["rejected_items"]) == 1
    assert agenda["rejected_items"][0]["candidate_id"] == "c_massively_exceeds"
    # c_fits_exactly takes the full budget
    assert len(agenda["ranked_items"]) == 1
    assert agenda["ranked_items"][0]["candidate_id"] == "c_fits_exactly"
    # c_slightly_exceeds is DEFERRED
    assert len(agenda["deferred_items"]) == 1
    assert agenda["deferred_items"][0]["candidate_id"] == "c_slightly_exceeds"
    print("PASS: Resource constraints correctly differentiate DEFERRED and REJECTED.")

def test_conflicting_observations_and_replay():
    print("--- Test: Conflicting Observations & Replay ---")
    # This requires using State engine CLI
    # We will simulate this by calling State transition via subprocess
    import state.transition
    prior_state = {
        "state_schema_version": "1.1.0",
        "confidence": 50,
        "evidence_count": 10,
        "applied_observation_ids": []
    }
    # Feed with two conflicting obs on same subject
    feed = {
        "observation_schema_version": "1.0.0",
        "kind": "feed",
        "observations": [
            {
                "observation_id": "OBS_00000000000000000000000000000001",
                "subject": "hypothesis_a",
                "support": 1,
                "reason_code": "EVALUATION_SUPPORTED",
                "source": {"run_id": "r1", "receipt_hash": "a"*64, "verification_root": "a"*64, "artifact_path": "a", "artifact_hash": "a"*64}
            },
            {
                "observation_id": "OBS_00000000000000000000000000000002",
                "subject": "hypothesis_a",
                "support": -1,
                "reason_code": "EVALUATION_CONTRADICTED",
                "source": {"run_id": "r2", "receipt_hash": "b"*64, "verification_root": "b"*64, "artifact_path": "b", "artifact_hash": "b"*64}
            }
        ]
    }
    spec = {
        "transition_spec_schema_version": "1.0.0",
        "transition_version": "t1",
        "subject": "hypothesis_a",
        "supported_increment": 5
    }
    
    t1 = state.transition.transition(prior_state, feed, spec)
    assert "OBS_00000000000000000000000000000001" in t1["applied_observation_ids"]
    assert "OBS_00000000000000000000000000000002" in t1["applied_observation_ids"]
    assert t1["summary"]["supported_applied"] == 1
    assert t1["summary"]["contradicted_applied"] == 1
    # Evidence count incremented only for supported
    assert t1["next_state"]["evidence_count"] == 10 + 5
    
    print("PASS: Conflicting observations recorded correctly.")
    
    # Replay test
    t2 = state.transition.transition(t1["next_state"], feed, spec)
    assert t2["summary"]["replayed_skipped"] == 2
    assert t2["summary"]["supported_applied"] == 0
    assert t2["summary"]["contradicted_applied"] == 0
    assert t2["next_state"]["evidence_count"] == 15
    assert t1["next_state"] == t2["next_state"]
    print("PASS: Replayed inputs ignored safely.")

def test_agenda_overflow():
    print("--- Test: Agenda Overflow ---")
    MAX_SAFE_INTEGER = 9007199254740991
    planner_input = {
        "planner_input_schema_version": "1.0.0",
        "state_root": "0"*64, "strategy_decision_root": "0"*64,
        "candidates": [
            {
                "candidate_id": "c1",
                "expected_information_gain": MAX_SAFE_INTEGER,
                "estimated_compute_cost": 0,
                "estimated_attention_cost": 0,
                "experiment_spec_root": "0"*64
            }
        ]
    }
    planner_spec = {
        "planner_spec_schema_version": "1.0.0",
        "gain_weight": 2, "compute_cost_weight": 1, "attention_cost_weight": 1,
        "max_agenda_items": 1, "max_compute_budget": 1, "max_attention_budget": 1
    }
    agenda = generate_agenda(planner_input, planner_spec)
    assert agenda["status"] == "FAILED_INPUT_VALIDATION"
    assert "AGENDA_SCORE_OVERFLOW" in agenda["reason_codes"]
    print("PASS: Agenda score overflow handled correctly.")

def test_observation_unobservable():
    print("--- Test: Observation Unobservable ---")
    import observation.extractor
    # Pass a valid receipt but an empty ver_art that fails lab_schema validation
    receipt = {
        "run_id": "x",
        "evaluation": {"overall_result": True},
        "artifacts": {"a": "h"}
    }
    eval_artifact = {
        "evaluation_schema_version": "1.0.0",
        "outcome": "SUPPORTED",
        "subject": "hypothesis_a",
        "metric": "score",
        "observed": 10,
        "expected": 5
    }
    feed = observation.extractor.extract_feed(
        receipt, {}, "a", eval_artifact, "h"
    )
    assert feed["kind"] == "failure"
    assert feed["status"] == "UNOBSERVABLE"
    assert feed["reason_code"] == "LABORATORY_VERIFICATION_ARTIFACT_INVALID"
    print("PASS: Observation unobservable schema invalidation handled correctly.")

def test_deterministic_failure_identity():
    print("--- Test: Deterministic Failure Identity ---")
    planner_input = {
        "planner_input_schema_version": "1.0.0",
        "state_root": "0"*64, "strategy_decision_root": "0"*64,
        "candidates": [
            {
                "candidate_id": "c1",
                "expected_information_gain": 10,
                "estimated_compute_cost": 0,
                "estimated_attention_cost": 0,
                "experiment_spec_root": "0"*64
            },
            {
                "candidate_id": "c1", # Duplicate!
                "expected_information_gain": 20,
                "estimated_compute_cost": 0,
                "estimated_attention_cost": 0,
                "experiment_spec_root": "0"*64
            }
        ]
    }
    planner_spec = {
        "planner_spec_schema_version": "1.0.0",
        "gain_weight": 1, "compute_cost_weight": 1, "attention_cost_weight": 1,
        "max_agenda_items": 1, "max_compute_budget": 1, "max_attention_budget": 1
    }
    agenda1 = generate_agenda(planner_input, planner_spec)
    agenda2 = generate_agenda(planner_input, planner_spec)
    assert agenda1 == agenda2
    assert agenda1["status"] == "FAILED_INPUT_VALIDATION"
    assert "DUPLICATE_CANDIDATE_ID" in agenda1["reason_codes"]
    print("PASS: Failure artifacts deterministically identical.")

def test_agenda_zero_weights():
    print("--- Test: Agenda Zero Weights ---")
    planner_input = {
        "planner_input_schema_version": "1.0.0",
        "state_root": "0"*64, "strategy_decision_root": "0"*64,
        "candidates": [
            {
                "candidate_id": "c1",
                "expected_information_gain": 100,
                "estimated_compute_cost": 10,
                "estimated_attention_cost": 10,
                "experiment_spec_root": "0"*64
            }
        ]
    }
    planner_spec = {
        "planner_spec_schema_version": "1.0.0",
        "gain_weight": 0, "compute_cost_weight": 0, "attention_cost_weight": 0,
        "max_agenda_items": 1, "max_compute_budget": 10, "max_attention_budget": 10
    }
    agenda = generate_agenda(planner_input, planner_spec)
    assert agenda["status"] == "SUCCESS"
    assert agenda["ranked_items"][0]["score"] == 0
    print("PASS: Agenda zero weights handled safely.")

def test_exact_64_hex_enforcement():
    print("--- Test: Exact 64-Hex Enforcement ---")
    planner_input = {
        "planner_input_schema_version": "1.0.0",
        "state_root": "invalid_root_length", "strategy_decision_root": "0"*64,
        "candidates": []
    }
    planner_spec = {
        "planner_spec_schema_version": "1.0.0",
        "gain_weight": 1, "compute_cost_weight": 1, "attention_cost_weight": 1,
        "max_agenda_items": 1, "max_compute_budget": 10, "max_attention_budget": 10
    }
    agenda = generate_agenda(planner_input, planner_spec)
    assert agenda["status"] == "FAILED_INPUT_VALIDATION"
    assert "planner_input_root" in agenda
    assert len(agenda["planner_input_root"]) == 64
    # Actually, let's just make sure it fails validation.
    print("PASS: 64-hex root enforcement tested.")

def main():
    test_api_cli_parity()
    test_version_vs_structural_mismatch()
    test_root_consistency()
    test_idempotence()
    test_boundary_integers()
    test_multiple_concurrent_hypotheses()
    test_resource_constrained_agendas()
    test_conflicting_observations_and_replay()
    test_agenda_overflow()
    test_observation_unobservable()
    test_deterministic_failure_identity()
    test_agenda_zero_weights()
    test_exact_64_hex_enforcement()
    print("\nALL STRESS TESTS PASSED.")

if __name__ == '__main__':
    main()
