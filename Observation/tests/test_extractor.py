import pytest
from observation.extractor import extract_feed
from jsonschema import ValidationError
from laboratory.crypto import canonical_hash
import copy

@pytest.fixture
def base_artifact():
    return {
        "evaluation_schema_version": "1.0.0",
        "outcome": "SUPPORTED",
        "subject": "strategy-hello-v1",
        "metric": "decision_reproduced",
        "observed": 1,
        "expected": 1
    }

@pytest.fixture
def base_receipt(base_artifact):
    return {
        "run_id": "RUN_123",
        "evaluation": {
            "overall_result": True
        },
        "artifacts": {
            "evaluation.json": canonical_hash(base_artifact)
        }
    }

def test_identical_inputs_produce_identical_feed(base_receipt, base_artifact):
    f1 = extract_feed(base_receipt, "evaluation.json", base_artifact, canonical_hash(base_artifact))
    f2 = extract_feed(copy.deepcopy(base_receipt), "evaluation.json", copy.deepcopy(base_artifact), canonical_hash(base_artifact))
    assert f1 == f2

def test_key_reordering(base_receipt, base_artifact):
    f1 = extract_feed(base_receipt, "evaluation.json", base_artifact, canonical_hash(base_artifact))
    
    r2 = {
        "artifacts": base_receipt["artifacts"],
        "evaluation": { "overall_result": True },
        "run_id": "RUN_123"
    }
    a2 = {
        "expected": 1,
        "observed": 1,
        "metric": "decision_reproduced",
        "subject": "strategy-hello-v1",
        "outcome": "SUPPORTED",
        "evaluation_schema_version": "1.0.0"
    }
    f2 = extract_feed(r2, "evaluation.json", a2, canonical_hash(a2))
    assert f1 == f2

def test_outcome_mapping(base_receipt, base_artifact):
    f = extract_feed(base_receipt, "evaluation.json", base_artifact, canonical_hash(base_artifact))
    assert f["observations"][0]["support"] == 1
    
    a2 = copy.deepcopy(base_artifact)
    a2["outcome"] = "INCONCLUSIVE"
    r2 = copy.deepcopy(base_receipt)
    r2["artifacts"]["evaluation.json"] = canonical_hash(a2)
    f2 = extract_feed(r2, "evaluation.json", a2, canonical_hash(a2))
    assert f2["observations"][0]["support"] == 0
    
    a3 = copy.deepcopy(base_artifact)
    a3["outcome"] = "CONTRADICTED"
    r3 = copy.deepcopy(base_receipt)
    r3["artifacts"]["evaluation.json"] = canonical_hash(a3)
    f3 = extract_feed(r3, "evaluation.json", a3, canonical_hash(a3))
    assert f3["observations"][0]["support"] == -1

def test_failed_execution(base_receipt, base_artifact):
    base_receipt["evaluation"]["overall_result"] = False
    res = extract_feed(base_receipt, "evaluation.json", base_artifact, canonical_hash(base_artifact))
    assert res["status"] == "UNOBSERVABLE"
    assert res["reason_code"] == "LABORATORY_RUN_NOT_VERIFIED"

def test_undeclared_artifact(base_receipt, base_artifact):
    with pytest.raises(ValueError, match="not declared"):
        extract_feed(base_receipt, "missing.json", base_artifact, canonical_hash(base_artifact))

def test_artifact_hash_mismatch(base_receipt, base_artifact):
    base_artifact["observed"] = 2
    # passing a mismatching hash
    with pytest.raises(ValueError, match="hash mismatch"):
        extract_feed(base_receipt, "evaluation.json", base_artifact, canonical_hash(base_artifact))

def test_changed_artifact_changes_id(base_receipt, base_artifact):
    f1 = extract_feed(base_receipt, "evaluation.json", base_artifact, canonical_hash(base_artifact))
    
    a2 = copy.deepcopy(base_artifact)
    a2["subject"] = "other-subject"
    r2 = copy.deepcopy(base_receipt)
    r2["artifacts"]["evaluation.json"] = canonical_hash(a2)
    
    f2 = extract_feed(r2, "evaluation.json", a2, canonical_hash(a2))
    assert f1["observations"][0]["observation_id"] != f2["observations"][0]["observation_id"]

def test_unmodified_inputs(base_receipt, base_artifact):
    r = copy.deepcopy(base_receipt)
    a = copy.deepcopy(base_artifact)
    extract_feed(r, "evaluation.json", a, canonical_hash(a))
    assert r == base_receipt
    assert a == base_artifact

def test_float_rejected(base_receipt, base_artifact):
    base_artifact["observed"] = 1.5
    with pytest.raises((ValidationError, ValueError)):
        # canonical hash calculation will throw ValueError
        try:
            h = canonical_hash(base_artifact)
        except ValueError:
            h = "0"*64
            raise ValueError
        extract_feed(base_receipt, "evaluation.json", base_artifact, h)

def test_oversized_integer_rejected(base_receipt, base_artifact):
    base_artifact["observed"] = 9007199254740992
    with pytest.raises((ValidationError, ValueError)):
        try:
            h = canonical_hash(base_artifact)
        except ValueError:
            raise ValueError
        extract_feed(base_receipt, "evaluation.json", base_artifact, h)
