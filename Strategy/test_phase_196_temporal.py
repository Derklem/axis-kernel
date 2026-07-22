import os
import sys
import copy
import json
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_DIR = os.path.join(BASE_DIR, "Audit")
sys.path.append(AUDIT_DIR)

from constitutional_debt_engine import ConstitutionalDebtEngine

def assert_no_mutation(original_rules, current_rules):
    assert json.dumps(original_rules, sort_keys=True) == json.dumps(current_rules, sort_keys=True), "FATAL: Engine mutated the active rules list in memory."

# Helper constants
DAY = 86400
CURRENT_TIME = 1000000000

def get_engine():
    return ConstitutionalDebtEngine(current_time=CURRENT_TIME)

def run_test_class_a():
    print("\n--- Test Class A: Fresh telemetry accepted ---")
    engine = get_engine()
    active_rules = [{"id": "RULE_A", "regex": "legacy_check", "authorized_timestamp": 1000}]
    original_rules = copy.deepcopy(active_rules)
    
    # Fresh: observed 1 hour ago, submitted 30 mins ago
    receipts = [{
        "type": "FP", "weight": 20.0, "source": "n1", "nonce": "nonceA1",
        "observation_time": CURRENT_TIME - 3600,
        "submission_time": CURRENT_TIME - 1800
    }]
    
    # Calling it once triggers immediate repeal because utility = 0 - 20 - 0 - 1 = -21 <= -10
    alerts = engine.audit_constitutional_debt(active_rules, {"RULE_A": receipts})
    repeal = any(a["type"] == "REPEAL_PROPOSAL" for a in alerts)
    assert repeal, "Class A Failed: Fresh telemetry should have been fully accepted."
    assert_no_mutation(original_rules, active_rules)
    print("Class A Passed: Fresh telemetry accepted.")

def run_test_class_b():
    print("\n--- Test Class B: Stale telemetry decayed/rejected ---")
    # Test decay > 30 days
    engine = get_engine()
    active_rules = [{"id": "RULE_B", "regex": "legacy_check", "authorized_timestamp": 1000}]
    original_rules = copy.deepcopy(active_rules)
    
    receipts = [{
        "type": "FP", "weight": 10.0, "source": "n1", "nonce": "nonceB1",
        "observation_time": CURRENT_TIME - (40 * DAY), # >30 days stale
        "submission_time": CURRENT_TIME - (40 * DAY)
    }]
    
    # weight 10.0 -> *0.5 (decay) = 5.0 -> utility = -6.0. Doesn't hit immediate repeal (-10)
    alerts = engine.audit_constitutional_debt(active_rules, {"RULE_B": receipts})
    assert not any(a["type"] == "REPEAL_PROPOSAL" for a in alerts), "Class B Failed: Stale telemetry was not decayed."
    
    # Test reject > 90 days
    receipts_reject = [{
        "type": "FP", "weight": 100.0, "source": "n1", "nonce": "nonceB2",
        "observation_time": CURRENT_TIME - (100 * DAY), # >90 days stale
        "submission_time": CURRENT_TIME - (100 * DAY)
    }]
    alerts_reject = engine.audit_constitutional_debt(active_rules, {"RULE_B": receipts_reject})
    assert not any(a["type"] == "REPEAL_PROPOSAL" for a in alerts_reject), "Class B Failed: >90 day telemetry was not rejected."
    
    assert_no_mutation(original_rules, active_rules)
    print("Class B Passed: Stale telemetry correctly decayed and rejected.")

def run_test_class_c():
    print("\n--- Test Class C: Replayed nonce rejected ---")
    engine = get_engine()
    active_rules = [{"id": "RULE_C", "regex": "legacy_check", "authorized_timestamp": 1000}]
    original_rules = copy.deepcopy(active_rules)
    
    receipts = [
        {
            "type": "FP", "weight": 20.0, "source": "n1", "nonce": "SAME_NONCE",
            "observation_time": CURRENT_TIME - 3600, "submission_time": CURRENT_TIME - 1800
        },
        {
            "type": "FP", "weight": 20.0, "source": "n1", "nonce": "SAME_NONCE",
            "observation_time": CURRENT_TIME - 3600, "submission_time": CURRENT_TIME - 1800
        }
    ]
    
    alerts = engine.audit_constitutional_debt(active_rules, {"RULE_C": receipts})
    replay_alert = any(a["type"] == "TEMPORAL_REPLAY_ALERT" for a in alerts)
    assert replay_alert, "Class C Failed: Replay alert not emitted."
    
    # Weight should only be 20.0 (utility -21). If it counted both, it'd be 40.0. 
    # Let's ensure it hits repeal, meaning at least 1 counted.
    assert any(a["type"] == "REPEAL_PROPOSAL" for a in alerts)
    
    # Second audit with same nonce should completely ignore it
    alerts2 = engine.audit_constitutional_debt(active_rules, {"RULE_C": [receipts[0]]})
    assert not any(a["type"] == "REPEAL_PROPOSAL" for a in alerts2), "Class C Failed: Nonce state not persisted across audits."
    
    assert_no_mutation(original_rules, active_rules)
    print("Class C Passed: Replayed nonce rejected globally.")

def run_test_class_d():
    print("\n--- Test Class D: Delayed telemetry discounted ---")
    engine = get_engine()
    active_rules = [{"id": "RULE_D", "regex": "legacy_check", "authorized_timestamp": 1000}]
    original_rules = copy.deepcopy(active_rules)
    
    # Delayed > 7 days, uncorroborated (discounted by 0.5)
    # Weight 20.0 -> *0.5 = 10.0
    # Also uncorroborated provenance multiplier = 0.5 -> 20 * 0.5 * 0.5 = 5.0
    receipts1 = [{
        "type": "FP", "weight": 20.0, "source": "n1", "nonce": "nonceD1",
        "observation_time": CURRENT_TIME - (10 * DAY),
        "submission_time": CURRENT_TIME - (1 * DAY),
        "corroboration": []
    }]
    alerts1 = engine.audit_constitutional_debt(active_rules, {"RULE_D": receipts1})
    assert not any(a["type"] == "REPEAL_PROPOSAL" for a in alerts1), "Class D Failed: Delayed uncorroborated telemetry not discounted enough."
    
    # Delayed > 7 days, corroborated (discounted by 0.8)
    # Provenance weight 1.0 -> 20 * 1.0 * 0.8 = 16.0
    receipts2 = [{
        "type": "FP", "weight": 20.0, "source": "n1", "nonce": "nonceD2",
        "observation_time": CURRENT_TIME - (10 * DAY),
        "submission_time": CURRENT_TIME - (1 * DAY),
        "corroboration": ["n2"]
    }]
    alerts2 = engine.audit_constitutional_debt(active_rules, {"RULE_D": receipts2})
    assert any(a["type"] == "REPEAL_PROPOSAL" for a in alerts2), "Class D Failed: Corroborated delayed telemetry discounted too heavily."
    
    assert_no_mutation(original_rules, active_rules)
    print("Class D Passed: Delayed telemetry discounted correctly based on corroboration.")

def run_test_class_e():
    print("\n--- Test Class E: Pre-audit burst quarantined ---")
    engine = get_engine()
    active_rules = [{"id": "RULE_E", "regex": "legacy_check", "authorized_timestamp": 1000}]
    original_rules = copy.deepcopy(active_rules)
    
    # 30 late submissions within 1 day of audit from same source
    receipts = []
    for i in range(30):
        receipts.append({
            "type": "FP", "weight": 1.0, "source": "n1", "nonce": f"nonceE{i}",
            "observation_time": CURRENT_TIME - (10 * DAY),
            "submission_time": CURRENT_TIME - 3600, # 1 hr ago
            "corroboration": ["n2"] # Bypass Phase 195 poison detection to isolate Phase 196 Burst
        })
        
    alerts = engine.audit_constitutional_debt(active_rules, {"RULE_E": receipts})
    burst_alert = any(a["type"] == "TEMPORAL_BURST_ALERT" for a in alerts)
    assert burst_alert, "Class E Failed: Burst alert not triggered."
    assert not any(a["type"] == "REPEAL_PROPOSAL" for a in alerts), "Class E Failed: Quarantined burst still caused repeal."
    
    assert_no_mutation(original_rules, active_rules)
    print("Class E Passed: Pre-audit dump quarantined.")

def run_test_class_f():
    print("\n--- Test Class F: Legitimate burst allowed ---")
    engine = get_engine()
    active_rules = [{"id": "RULE_F", "regex": "legacy_check", "authorized_timestamp": 1000}]
    original_rules = copy.deepcopy(active_rules)
    
    # 30 late submissions within 1 day of audit, but split evenly across 3 sources (10 each)
    receipts = []
    for i in range(30):
        src = f"n{i % 3}"
        receipts.append({
            "type": "FP", "weight": 1.0, "source": src, "nonce": f"nonceF{i}",
            "observation_time": CURRENT_TIME - (10 * DAY),
            "submission_time": CURRENT_TIME - 3600,
            "corroboration": ["n_other"]
        })
        
    alerts = engine.audit_constitutional_debt(active_rules, {"RULE_F": receipts})
    burst_alert = any(a["type"] == "TEMPORAL_BURST_ALERT" for a in alerts)
    assert not burst_alert, "Class F Failed: Legitimate multi-source burst was quarantined."
    
    assert_no_mutation(original_rules, active_rules)
    print("Class F Passed: Multi-source convergence permitted.")

def run_test_class_g():
    print("\n--- Test Class G: Missing fields & Future timestamps ---")
    engine = get_engine()
    active_rules = [{"id": "RULE_G", "regex": "legacy_check", "authorized_timestamp": 1000}]
    original_rules = copy.deepcopy(active_rules)
    
    receipts = [
        # Missing fields
        {"type": "FP", "weight": 20.0, "source": "n1", "nonce": "nonceG1"},
        # Future timestamp
        {
            "type": "FP", "weight": 20.0, "source": "n1", "nonce": "nonceG2",
            "observation_time": CURRENT_TIME + 3600, "submission_time": CURRENT_TIME + 1800
        }
    ]
    
    alerts = engine.audit_constitutional_debt(active_rules, {"RULE_G": receipts})
    fraud_alert = any(a["type"] == "TEMPORAL_FRAUD_ALERT" for a in alerts)
    assert fraud_alert, "Class G Failed: Fraud alert not emitted for future timestamp."
    assert not any(a["type"] == "REPEAL_PROPOSAL" for a in alerts), "Class G Failed: Inadmissible receipts caused repeal."
    
    assert_no_mutation(original_rules, active_rules)
    print("Class G Passed: Missing fields dropped, future timestamps flagged.")

if __name__ == "__main__":
    print("Beginning Phase 196 Temporal Provenance Tests...")
    run_test_class_a()
    run_test_class_b()
    run_test_class_c()
    run_test_class_d()
    run_test_class_e()
    run_test_class_f()
    run_test_class_g()
    print("\nAll Phase 196 tests passed successfully.")
