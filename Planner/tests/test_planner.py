import pytest
from Planner.service import build_agenda
from Planner.intake import load_policy

def test_planner_v0():
    # Setup test policy & constraints
    policy_id = "agenda_v1_uncertainty_age_cost"
    constraints = {
        "resolved_dependencies": set(["DEP_1"]),
        "max_compute_minutes": 100
    }
    now_utc = 1700000000.0

    candidates = [
        # Valid candidate 1
        {
            "candidate_id": "TASK_1",
            "title": "Valid task",
            "objective": "Test",
            "source_refs": [],
            "expected_information_gain": 0.8,
            "epistemic_debt_age_hours": 10.0,
            "attention_cost": "acceptable",
            "estimated_compute_minutes": 20,
            "dependencies": ["DEP_1"],
            "constraints": [],
            "risk_level": "YELLOW",
            "execution_mode": "autonomous",
            "status": "candidate"
        },
        # Valid candidate 2 (Higher IG, should rank higher)
        {
            "candidate_id": "TASK_2",
            "title": "Another valid task",
            "objective": "Test",
            "source_refs": [],
            "expected_information_gain": 0.9,
            "epistemic_debt_age_hours": 10.0,
            "attention_cost": "acceptable",
            "estimated_compute_minutes": 20,
            "dependencies": [],
            "constraints": [],
            "risk_level": "GREEN",
            "execution_mode": "human_approval",
            "status": "candidate"
        },
        # Duplicate of TASK_1 (Will be rejected)
        {
            "candidate_id": "TASK_1",
            "title": "Duplicate",
            "objective": "Test",
            "source_refs": [],
            "expected_information_gain": 0.8,
            "epistemic_debt_age_hours": 10.0,
            "attention_cost": "acceptable",
            "estimated_compute_minutes": 20,
            "dependencies": ["DEP_1"],
            "constraints": [],
            "risk_level": "YELLOW",
            "execution_mode": "autonomous",
            "status": "candidate"
        },
        # Malformed candidate (missing expected_information_gain)
        {
            "candidate_id": "TASK_MALFORMED",
            "title": "Malformed",
            "objective": "Test",
            "source_refs": [],
            "epistemic_debt_age_hours": 10.0,
            "attention_cost": "acceptable",
            "estimated_compute_minutes": 20,
            "dependencies": [],
            "constraints": [],
            "risk_level": "GREEN",
            "execution_mode": "human_approval",
            "status": "candidate"
        },
        # Unresolved dependency
        {
            "candidate_id": "TASK_UNRESOLVED",
            "title": "Unresolved deps",
            "objective": "Test",
            "source_refs": [],
            "expected_information_gain": 0.8,
            "epistemic_debt_age_hours": 10.0,
            "attention_cost": "acceptable",
            "estimated_compute_minutes": 20,
            "dependencies": ["MISSING_DEP"],
            "constraints": [],
            "risk_level": "YELLOW",
            "execution_mode": "autonomous",
            "status": "candidate"
        }
    ]

    agenda = build_agenda(candidates, constraints, policy_id, now_utc)

    # Requirment 1: Valid candidates rank deterministically.
    assert len(agenda["tasks"]) == 2
    assert agenda["tasks"][0]["candidate_id"] == "TASK_2" # Has higher IG & lower risk
    assert agenda["tasks"][1]["candidate_id"] == "TASK_1"

    # Verify receipts
    receipts = agenda.get("receipts", [])
    assert len(receipts) == 5
    
    # Requirment 2: Malformed candidates fail closed
    malformed_receipt = next(r for r in receipts if r["candidate_id"] == "TASK_MALFORMED")
    assert malformed_receipt["status"] == "NEEDS_REVISION"
    assert any("SCHEMA_VIOLATION" in req for req in malformed_receipt["reasons"])

    # Requirment 3: Unresolved dependencies block execution
    unresolved_receipt = next(r for r in receipts if r["candidate_id"] == "TASK_UNRESOLVED")
    assert unresolved_receipt["status"] == "BLOCKED"
    assert "UNRESOLVED_DEPENDENCY:MISSING_DEP" in unresolved_receipt["reasons"]
    
    # Requirment 4: Duplicate candidates rejected deterministically
    dup_receipt = next(r for r in receipts if r["candidate_id"] == "TASK_1" and r["status"] == "DUPLICATE")
    assert dup_receipt["status"] == "DUPLICATE"

    # Requirment 5: Every candidate yields a decision receipt
    # (Checked by len(receipts) == 5)

    # Requirment 6: Output is mathematically reproducible
    agenda2 = build_agenda(candidates, constraints, policy_id, now_utc)
    import json
    assert json.dumps(agenda, sort_keys=True) == json.dumps(agenda2, sort_keys=True)
