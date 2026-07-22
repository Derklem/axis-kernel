import os
import sys
import copy
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_DIR = os.path.join(BASE_DIR, "Audit")
sys.path.append(AUDIT_DIR)

from constitutional_debt_engine import ConstitutionalDebtEngine
from telemetry_provenance import TelemetryAuthenticator

def assert_no_mutation(original_rules, current_rules):
    assert json.dumps(original_rules, sort_keys=True) == json.dumps(current_rules, sort_keys=True), "FATAL: Engine mutated the active rules list in memory."

def run_test_class_a(engine):
    print("\n--- Test Class A: Event Weighting ---")
    active_rules = [{"id": "RULE_A_WEIGHTING", "regex": "legacy_check", "authorized_timestamp": 1000}]
    original_rules = copy.deepcopy(active_rules)
    
    # Prove weight calculations
    receipts = [
        {"type": "FP", "event_class": "observed", "source": "node_a", "corroboration": ["node_b"]}, # 1.0 * 1.0 = 1.0
        {"type": "FP", "event_class": "inferred", "source": "node_a", "corroboration": ["node_b"]}, # 0.5 * 1.0 = 0.5
        {"type": "FP", "event_class": "reported", "source": "node_a", "corroboration": ["node_b"]}, # 0.2 * 1.0 = 0.2
        {"type": "FP", "event_class": "simulated", "source": "node_a", "corroboration": ["node_b"]} # 0.0 * 1.0 = 0.0
    ]
    
    auth = TelemetryAuthenticator()
    total_weighted_fp, _ = auth.process_receipts("RULE_A_WEIGHTING", receipts)
    
    # 1.0 + 0.5 + 0.2 + 0.0 = 1.7
    assert abs(total_weighted_fp - 1.7) < 0.001, f"Class A Failed: Expected 1.7, got {total_weighted_fp}"
    print("Class A Passed: Event weighting aligns with explicit discounting multipliers.")

def run_test_class_b(engine):
    print("\n--- Test Class B: Uncorroborated Decay ---")
    active_rules = [{"id": "RULE_B_CORROB", "regex": "legacy_check", "authorized_timestamp": 2000}]
    original_rules = copy.deepcopy(active_rules)
    
    # Uncorroborated decay multiplier is 0.5
    receipts = [
        {"type": "FP", "event_class": "observed", "source": "node_a", "corroboration": []}, # 1.0 * 0.5 = 0.5
        {"type": "FP", "event_class": "inferred", "source": "node_a", "corroboration": []}  # 0.5 * 0.5 = 0.25
    ]
    
    auth = TelemetryAuthenticator()
    total_weighted_fp, _ = auth.process_receipts("RULE_B_CORROB", receipts)
    
    # 0.5 + 0.25 = 0.75
    assert abs(total_weighted_fp - 0.75) < 0.001, f"Class B Failed: Expected 0.75, got {total_weighted_fp}"
    print("Class B Passed: Uncorroborated telemetry correctly halved.")

def run_test_class_c(engine):
    print("\n--- Test Class C: Measurement Poisoning Detection ---")
    active_rules = [{"id": "RULE_C_POISON", "regex": "legacy_check", "authorized_timestamp": 3000}]
    original_rules = copy.deepcopy(active_rules)
    
    # 1. Prove repeal WITHOUT provenance logic:
    # Here, we spoof the engine to just receive an overwhelming weighted FP that will trigger <= -10 immediately.
    # E.g. value = -1 - 20 = -21 <= -10. We pass corroboration to avoid the 0.5 decay shrinking it below 10.
    engine_temp = ConstitutionalDebtEngine()
    raw_telemetry = {"RULE_C_POISON": [{"type": "FP", "weight": 20.0, "corroboration": ["spoof"]}]}
    alerts_no_provenance = engine_temp.audit_constitutional_debt(active_rules, raw_telemetry)
    assert any(a["type"] == "REPEAL_PROPOSAL" for a in alerts_no_provenance), "Class C Failed: Expected repeal without provenance filtering."
    
    # 2. Prove survival WITH provenance logic:
    # 30 uncorroborated "observed" FPs from 'rogue_node'. 
    # Without provenance detection, total = 30 * 1.0 * 0.5 = 15.0 weighted FP. value = -16 <= -10.
    poison_receipts = [
        {"type": "FP", "event_class": "observed", "source": "rogue_node", "corroboration": []} for _ in range(30)
    ]
    engine_filtered = ConstitutionalDebtEngine()
    telemetry = {"RULE_C_POISON": poison_receipts}
    alerts_filtered = engine_filtered.audit_constitutional_debt(active_rules, telemetry)
    
    poison_alert_found = any(a["type"] == "TELEMETRY_POISONING_ALERT" for a in alerts_filtered)
    repeal_found = any(a["type"] == "REPEAL_PROPOSAL" for a in alerts_filtered)
    
    assert poison_alert_found, "Class C Failed: Did not emit TELEMETRY_POISONING_ALERT."
    assert not repeal_found, "Class C Failed: Emitted REPEAL_PROPOSAL despite poisoning detection."
    
    assert_no_mutation(original_rules, active_rules)
    print("Class C Passed: Rogue telemetry zero-weighted. Legitimate rule survived the attack.")

if __name__ == "__main__":
    engine = ConstitutionalDebtEngine()
    
    print("Beginning Phase 195 Telemetry Provenance Tests...")
    run_test_class_a(engine)
    run_test_class_b(engine)
    run_test_class_c(engine)
    
    print("\nAll Phase 195 tests passed successfully.")
