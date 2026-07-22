import os
import json
import hashlib
import hmac
import time
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Move state up from Audit/State/Distress to State/Distress
STRATEGY_DIR = os.path.dirname(BASE_DIR)
STATE_DIR = os.path.join(STRATEGY_DIR, "State", "Distress")

class DistressProtocol:
    def __init__(self):
        if not os.path.exists(STATE_DIR):
            os.makedirs(STATE_DIR, exist_ok=True)
        self.lock_file = os.path.join(STATE_DIR, "active_distress.json")
        self.receipts_log = os.path.join(STATE_DIR, "restoration_receipts.log")
        
    def is_in_distress(self):
        return os.path.exists(self.lock_file)
        
    def check_fatal_alerts(self, alerts):
        fatal_types = {"TEMPORAL_LEDGER_IO_ALERT"}
        for a in alerts:
            if a["type"] in fatal_types:
                self.enter_distress(a["type"], a["reason"], alerts)
                return True
        return False
        
    def enter_distress(self, trigger_type, reason, context_alerts):
        if self.is_in_distress():
            return
            
        distress_id = str(uuid.uuid4())
        timestamp = time.time()
        
        bundle = {
            "distress_id": distress_id,
            "timestamp": timestamp,
            "trigger_type": trigger_type,
            "reason": reason,
            "context_alerts": context_alerts
        }
        
        bundle_path = os.path.join(STATE_DIR, f"recovery_bundle_{distress_id}.json")
        with open(bundle_path, "w", encoding="utf-8") as f:
            json.dump(bundle, f, indent=2, sort_keys=True)
            
        # Calculate SHA256 of the bundle for the receipt
        bundle_bytes = json.dumps(bundle, sort_keys=True, separators=(",", ":")).encode("utf-8")
        bundle_hash = hashlib.sha256(bundle_bytes).hexdigest()
            
        lock_data = {
            "distress_id": distress_id,
            "bundle_path": bundle_path,
            "bundle_hash": bundle_hash,
            "locked_at": timestamp
        }
        
        with open(self.lock_file, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, indent=2)
            
        print(f"\n[!] CONSTITUTIONAL DISTRESS STATE ENGAGED [!]")
        print(f"Trigger: {trigger_type} - {reason}")
        print(f"Metabolism Halted. Recovery bundle generated at: {bundle_path}")
        print(f"Bundle Hash: {bundle_hash}")
        
    def attempt_restoration(self, receipt_json_path, receipt_sig_path):
        if not self.is_in_distress():
            return False, "Not in distress."
            
        if not os.path.exists(receipt_json_path) or not os.path.exists(receipt_sig_path):
            return False, "Receipt JSON or signature file missing."
            
        with open(receipt_sig_path, "r", encoding="utf-8") as f:
            provided_sig = f.read().strip()
            
        # Replay Defense
        sig_hash = hashlib.sha256(provided_sig.encode("utf-8")).hexdigest()
        
        with open(receipt_json_path, "r", encoding="utf-8") as f:
            receipt = json.load(f)
            
        replay_entry = f"{receipt.get('distress_id')}::{sig_hash}\n"
        if os.path.exists(self.receipts_log):
            with open(self.receipts_log, "r", encoding="utf-8") as f:
                if replay_entry in f.readlines():
                    return False, "Replay attack detected: This restoration receipt signature has already been used."
                    
        with open(self.lock_file, "r", encoding="utf-8") as f:
            lock_data = json.load(f)
            
        if receipt.get("schema") != "axis.restoration_receipt.v1":
            return False, "Invalid schema."
            
        if receipt.get("distress_id") != lock_data["distress_id"]:
            return False, "Receipt distress_id does not match active lock."
            
        if receipt.get("bundle_hash") != lock_data["bundle_hash"]:
            return False, "Receipt bundle_hash does not match active lock."
            
        if receipt.get("requested_action") != "CLEAR_CONSTITUTIONAL_DISTRESS_STATE":
            return False, "Invalid requested_action."
            
        # Validate HMAC
        secret = os.environ.get("AXIS_HMAC_SECRET")
        if not secret:
            return False, "AXIS_HMAC_SECRET not configured."
            
        canonical_bytes = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), canonical_bytes, hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(expected_sig, provided_sig):
            return False, "Cryptographic signature validation failed."
                    
        with open(self.receipts_log, "a", encoding="utf-8") as f:
            f.write(replay_entry)
            
        # Cleared!
        os.remove(self.lock_file)
        print("\n[SUCCESS] Restoration receipt verified. Constitutional distress state cleared.")
        return True, "Distress cleared."
