import os
import sys
import json
import hashlib
import hmac

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_DIR = os.path.join(BASE_DIR, "Audit")
STRATEGY_DIR = BASE_DIR
sys.path.append(AUDIT_DIR)

from constitutional_debt_engine import ConstitutionalDebtEngine

# Mock secret for the test
os.environ["AXIS_HMAC_SECRET"] = "test_secret_key"

def clear_distress_files():
    state_dir = os.path.join(STRATEGY_DIR, "State", "Distress")
    if os.path.exists(state_dir):
        for f in os.listdir(state_dir):
            os.remove(os.path.join(state_dir, f))

def get_engine():
    return ConstitutionalDebtEngine()

def run_tests():
    clear_distress_files()
    
    print("\n--- Test A: Distress Trigger on Ledger IO Error ---")
    engine = get_engine()
    # Force an IO error by mocking it on the temporal authenticator
    engine.temporal_authenticator.io_error = "Mocked Disk Corruption Exception"
    
    active_rules = [{"id": "RULE_197", "regex": "legacy", "authorized_timestamp": 1000}]
    
    # Run audit, it should fail closed and enter distress
    alerts = engine.audit_constitutional_debt(active_rules, {"RULE_197": []})
    
    # Should contain TEMPORAL_LEDGER_IO_ALERT and return mid-audit
    assert any(a["type"] == "TEMPORAL_LEDGER_IO_ALERT" for a in alerts), "Test A Failed: Did not emit IO alert."
    assert engine.distress_protocol.is_in_distress(), "Test A Failed: System did not enter CONSTITUTIONAL_DISTRESS_STATE."
    print("Test A Passed: Engine caught fatal error and entered distress.")
    
    print("\n--- Test B: Recovery Bundle Generation ---")
    lock_file = engine.distress_protocol.lock_file
    assert os.path.exists(lock_file), "Test B Failed: Lock file missing."
    with open(lock_file, "r") as f:
        lock_data = json.load(f)
        
    bundle_path = lock_data["bundle_path"]
    assert os.path.exists(bundle_path), "Test B Failed: Bundle file missing."
    with open(bundle_path, "r") as f:
        bundle_data = json.load(f)
        
    assert bundle_data["trigger_type"] == "TEMPORAL_LEDGER_IO_ALERT", "Test B Failed: Bundle missing trigger type."
    assert lock_data["distress_id"] == bundle_data["distress_id"], "Test B Failed: Distress ID mismatch."
    print("Test B Passed: Read-only recovery bundle generated correctly.")
    
    print("\n--- Test C: Metabolism Block ---")
    # Trying to run audit again
    engine2 = get_engine()
    alerts2 = engine2.audit_constitutional_debt(active_rules, {"RULE_197": []})
    assert len(alerts2) == 1 and alerts2[0]["type"] == "DISTRESS_LOCK", "Test C Failed: Engine ran during distress!"
    print("Test C Passed: Metabolism safely blocked while in distress.")
    
    print("\n--- Test D: Restoration Receipt ---")
    # Generate receipt payload
    receipt = {
        "schema": "axis.restoration_receipt.v1",
        "distress_id": lock_data["distress_id"],
        "bundle_hash": lock_data["bundle_hash"],
        "requested_action": "CLEAR_CONSTITUTIONAL_DISTRESS_STATE",
        "signer_id": "test_operator",
        "issued_utc": "12345"
    }
    receipt_json_path = os.path.join(STRATEGY_DIR, "State", "Distress", "mock_receipt.json")
    with open(receipt_json_path, "w") as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
        
    # Sign it
    canonical_bytes = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
    secret = os.environ["AXIS_HMAC_SECRET"]
    sig = hmac.new(secret.encode("utf-8"), canonical_bytes, hashlib.sha256).hexdigest()
    
    receipt_sig_path = os.path.join(STRATEGY_DIR, "State", "Distress", "mock_receipt.sig")
    with open(receipt_sig_path, "w") as f:
        f.write(sig)
        
    # Attempt restoration
    success, msg = engine2.distress_protocol.attempt_restoration(receipt_json_path, receipt_sig_path)
    assert success, f"Test D Failed: Restoration rejected - {msg}"
    assert not engine2.distress_protocol.is_in_distress(), "Test D Failed: Lock file not removed."
    print("Test D Passed: Valid HMAC restoration receipt cleared distress state.")
    
    # Confirm metabolism resumed
    engine2.temporal_authenticator.io_error = None # Fix the original issue
    alerts_resumed = engine2.audit_constitutional_debt(active_rules, {"RULE_197": []})
    assert not any(a["type"] == "DISTRESS_LOCK" for a in alerts_resumed), "Test D Failed: Still locked after restoration."
    
    print("\n--- Test E: Replay Defense ---")
    # Force distress again
    engine2.temporal_authenticator.io_error = "Second mock error"
    engine2.audit_constitutional_debt(active_rules, {"RULE_197": []})
    assert engine2.distress_protocol.is_in_distress()
    
    # Re-use the exact same signature (which is fundamentally tied to the old distress ID, but let's say the attacker tries it anyway, or modifies distress_id but same sig)
    # The signature itself is tracked.
    success2, msg2 = engine2.distress_protocol.attempt_restoration(receipt_json_path, receipt_sig_path)
    assert not success2 and "Replay attack detected" in msg2, "Test E Failed: Replayed signature was allowed."
    print("Test E Passed: Replayed signature was blocked.")

if __name__ == "__main__":
    print("Beginning Phase 197 Distress & Recovery Tests...")
    run_tests()
    print("\nAll Phase 197 tests passed successfully.")
