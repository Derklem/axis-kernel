import os
import sys
import copy
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_DIR = os.path.join(BASE_DIR, "Audit")
sys.path.append(AUDIT_DIR)

from constitutional_debt_engine import ConstitutionalDebtEngine

def assert_no_mutation(original_rules, current_rules):
    # Ensure exact match to prove no mutation occurred
    assert json.dumps(original_rules, sort_keys=True) == json.dumps(current_rules, sort_keys=True), "FATAL: Engine mutated the active rules list in memory."

def run_test_class_a(engine):
    print("\n--- Test Class A: Marginal Utility & Persistence ---")
    active_rules = [
        {"id": "RULE_A_OBSOLETE", "regex": "legacy_check", "authorized_timestamp": 1000}
    ]
    original_rules = copy.deepcopy(active_rules)
    
    receipts_cycle = [
        {"type": "FP", "weight": 1.0},
        {"type": "FP", "weight": 1.0}
    ]
    telemetry = {"RULE_A_OBSOLETE": receipts_cycle}
    
    # Cycle 1
    alerts1 = engine.audit_constitutional_debt(active_rules, telemetry)
    assert not any(a["type"] == "REPEAL_PROPOSAL" for a in alerts1), "Failed: Alerted too soon (persistence check failed)."
    assert_no_mutation(original_rules, active_rules)
    
    # Cycle 2
    alerts2 = engine.audit_constitutional_debt(active_rules, telemetry)
    assert not any(a["type"] == "REPEAL_PROPOSAL" for a in alerts2), "Failed: Alerted too soon (persistence check failed)."
    assert_no_mutation(original_rules, active_rules)
    
    # Cycle 3
    alerts3 = engine.audit_constitutional_debt(active_rules, telemetry)
    repeal_found = any(a["type"] == "REPEAL_PROPOSAL" and a["rule_id"] == "RULE_A_OBSOLETE" for a in alerts3)
    assert repeal_found, "Class A Test Failed: Did not emit REPEAL_PROPOSAL after 3 negative audits."
    assert_no_mutation(original_rules, active_rules)
    
    # Cycle 4 (Catastrophic failure)
    catastrophic_telemetry = {"RULE_A_OBSOLETE": [{"type": "FP", "weight": 10.0}]}
    engine_fresh = ConstitutionalDebtEngine()
    alerts4 = engine_fresh.audit_constitutional_debt(active_rules, catastrophic_telemetry)
    catastrophic_found = any(a["type"] == "REPEAL_PROPOSAL" and "Immediate" in a["reason"] for a in alerts4)
    assert catastrophic_found, "Class A Test Failed: Did not immediately emit REPEAL_PROPOSAL for <= -10 value."
    assert_no_mutation(original_rules, active_rules)
    
    print("Class A Passed: Detected obsolete defense and asserted NO MUTATION.")

def run_test_class_b(engine):
    print("\n--- Test Class B: Redundancy & Coverage Illusion ---")
    active_rules = [
        {"id": "RULE_B_BROAD", "regex": "streamline", "authorized_timestamp": 2000},
        {"id": "RULE_B_NARROW", "regex": "streamline confidence aggregation", "authorized_timestamp": 2001}
    ]
    original_rules = copy.deepcopy(active_rules)
    
    alerts = engine.audit_constitutional_debt(active_rules)
    
    conflict_found = any(a["type"] == "REDUNDANCY_ALERT" and "RULE_B_NARROW" in a["rule_id"] for a in alerts)
    assert conflict_found, "Class B Test Failed: Did not emit REDUNDANCY_ALERT for coverage illusion."
    assert_no_mutation(original_rules, active_rules)
    
    print("Class B Passed: Detected redundancy based on chronological coverage and asserted NO MUTATION.")

def run_test_class_c(engine):
    print("\n--- Test Class C: Defensive Sclerosis ---")
    active_rules = []
    
    sclerosis_detected = False
    for cycle in range(1, 15):
        active_rules.append({
            "id": f"RULE_CYCLE_{cycle}", 
            "regex": f"non_existent_hostile_{cycle}", 
            "authorized_timestamp": 3000 + cycle
        })
        original_rules = copy.deepcopy(active_rules)
        
        alerts = engine.audit_constitutional_debt(active_rules)
        assert_no_mutation(original_rules, active_rules)
        
        if any(a["type"] == "SCLEROSIS_ALERT" for a in alerts):
            sclerosis_detected = True
            print(f"Sclerosis Alert triggered at rule count {len(active_rules)}.")
            break
            
    assert sclerosis_detected, "Class C Test Failed: Did not emit SCLEROSIS_ALERT for 10 sequential negative/zero value rules."
    print("Class C Passed: Detected rolling systemic defensive sclerosis and asserted NO MUTATION.")

if __name__ == "__main__":
    engine = ConstitutionalDebtEngine()
    
    print("Beginning Phase 194.1 Marginal Utility Tests...")
    run_test_class_a(engine)
    run_test_class_b(engine)
    run_test_class_c(engine)
    
    print("\nAll Phase 194.1 tests passed successfully.")
