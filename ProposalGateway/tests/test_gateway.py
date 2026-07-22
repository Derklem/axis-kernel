import pytest
import json
from ProposalGateway.gateway import evaluate_proposal

def test_repeated_evaluation_identical_receipt_ids():
    raw_text = '{"objective": "A", "status": "candidate"}'
    res1 = evaluate_proposal(raw_text, {}, 100.0)
    res2 = evaluate_proposal(raw_text, {}, 100.0)
    assert res1["receipt"]["gateway_receipt_id"] == res2["receipt"]["gateway_receipt_id"]

def test_different_source_context_different_receipt_ids():
    raw_text = '{"objective": "A", "status": "candidate"}'
    res1 = evaluate_proposal(raw_text, {"allowed": set(["A"])}, 100.0)
    res2 = evaluate_proposal(raw_text, {"allowed": set(["B"])}, 100.0)
    assert res1["receipt"]["gateway_receipt_id"] != res2["receipt"]["gateway_receipt_id"]

def test_semantically_equivalent_formatting_same_candidate_id():
    base = {
        "title": "A",
        "objective": "Test",
        "expected_information_gain": "0.5",
        "epistemic_debt_age_hours": 10.0,
        "attention_cost": "acceptable",
        "estimated_compute_minutes": 20.0,
        "dependencies": [],
        "constraints": [],
        "execution_mode": "autonomous",
        "source_refs": ["REF_1"]
    }
    raw1_dict = dict(base, risk_level="green")
    raw2_dict = dict(base, risk_level=" GREEN ")
    raw1 = json.dumps(raw1_dict)
    raw2 = json.dumps(raw2_dict, indent=2)
    
    res1 = evaluate_proposal(raw1, {"allowed_source_refs": set(["REF_1"])}, 100.0)
    res2 = evaluate_proposal(raw2, {"allowed_source_refs": set(["REF_1"])}, 100.0)
    assert res1["candidate"] is not None
    assert res2["candidate"] is not None
    assert res1["candidate"]["candidate_id"] == res2["candidate"]["candidate_id"]

def test_duplicate_json_keys_rejected():
    raw = '{"objective": "A", "objective": "B"}'
    res = evaluate_proposal(raw, {}, 100.0)
    assert res["gateway_status"] == "REJECTED"
    assert any("DUPLICATE_JSON_KEY" in r for r in res["receipt"]["reason_codes"])

def test_multiple_objects_and_trailing_garbage_rejected():
    raw_multiple = '{"objective": "A"}{"objective": "B"}'
    res1 = evaluate_proposal(raw_multiple, {}, 100.0)
    assert res1["gateway_status"] == "REJECTED"
    assert any("TRAILING_CONTENT_DETECTED" in r for r in res1["receipt"]["reason_codes"])
    
    raw_garbage = '{"objective": "A"}  trailing garbage'
    res2 = evaluate_proposal(raw_garbage, {}, 100.0)
    assert res2["gateway_status"] == "REJECTED"

def test_nan_and_infinity_rejected():
    raw = '{"objective": "A", "expected_information_gain": NaN}'
    res = evaluate_proposal(raw, {}, 100.0)
    assert res["gateway_status"] == "REJECTED"
    assert any("NON_FINITE_NUMBER" in r for r in res["receipt"]["reason_codes"])

def test_missing_substantive_yields_needs_revision():
    raw = """
    {
        "title": "A",
        "objective": "Test",
        "expected_information_gain": 0.5,
        "attention_cost": "acceptable",
        "estimated_compute_minutes": 20.0,
        "dependencies": [],
        "constraints": [],
        "risk_level": "GREEN",
        "execution_mode": "autonomous",
        "source_refs": ["REF_1"]
    }
    """
    res = evaluate_proposal(raw, {"allowed_source_refs": set(["REF_1"])}, 100.0)
    assert res["gateway_status"] == "NEEDS_REVISION"
    assert any("MISSING_FIELD:epistemic_debt_age_hours" in r for r in res["receipt"]["reason_codes"])

def test_unknown_fields_hashed_in_receipt():
    raw = """
    {
        "title": "A",
        "objective": "Test",
        "expected_information_gain": 0.5,
        "epistemic_debt_age_hours": 10.0,
        "attention_cost": "acceptable",
        "estimated_compute_minutes": 20.0,
        "dependencies": [],
        "constraints": [],
        "risk_level": "GREEN",
        "execution_mode": "autonomous",
        "source_refs": ["REF_1"],
        "recommended_shell_command": "rm -rf /"
    }
    """
    res = evaluate_proposal(raw, {"allowed_source_refs": set(["REF_1"])}, 100.0)
    assert res["gateway_status"] == "NEEDS_REVISION"
    assert any("UNKNOWN_FIELD:recommended_shell_command" in r for r in res["receipt"]["reason_codes"])
    assert len(res["receipt"]["unknown_fields"]) == 1
    assert res["receipt"]["unknown_fields"][0]["field_name"] == "recommended_shell_command"
    assert "value_hash" in res["receipt"]["unknown_fields"][0]

def test_gateway_accepted_passes_planner_candidate_validation():
    raw = """
    ```json
    {
        "title": "Valid Task",
        "objective": "Test",
        "expected_information_gain": "0.5",
        "epistemic_debt_age_hours": 10.0,
        "attention_cost": " acceptable ",
        "estimated_compute_minutes": "20",
        "dependencies": ["B", "A"],
        "constraints": [],
        "risk_level": "green",
        "execution_mode": "AUTONOMOUS",
        "source_refs": ["REF_1"]
    }
    ```
    """
    res = evaluate_proposal(raw, {"allowed_source_refs": set(["REF_1"])}, 100.0)
    assert res["gateway_status"] == "ACCEPTED_WITH_SAFE_REPAIRS"
    # No PLANNER_SCHEMA_ERROR
    assert not any("PLANNER_SCHEMA_ERROR" in r for r in res["receipt"]["reason_codes"])
