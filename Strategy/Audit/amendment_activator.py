import os
import sys
import json
import time
import shutil
import argparse
import hashlib
import hmac

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_STRAT_DIR = os.path.dirname(_TEST_DIR)

PROPOSED_DEFENSES_DIR = os.path.join(_STRAT_DIR, "State", "ProposedDefenses")
AUTHORIZED_AMENDMENTS_DIR = os.path.join(_STRAT_DIR, "State", "AuthorizedAmendments")

from amendment_court import evaluate_candidate_regex

def setup_directories():
    os.makedirs(PROPOSED_DEFENSES_DIR, exist_ok=True)
    os.makedirs(AUTHORIZED_AMENDMENTS_DIR, exist_ok=True)

def canonicalize_payload(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')

def get_ledger_path():
    return os.path.join(AUTHORIZED_AMENDMENTS_DIR, "signature_receipts.log")

def load_signature_ledger():
    ledger_path = get_ledger_path()
    if not os.path.exists(ledger_path):
        return set()
    with open(ledger_path, "r", encoding="utf-8") as f:
        return set(line.strip().split(",")[0] for line in f if line.strip())

def append_to_ledger(signature, payload_hash, authorized_filename):
    with open(get_ledger_path(), "a", encoding="utf-8") as f:
        f.write(f"{signature},{payload_hash},{authorized_filename}\n")

def activate_amendments():
    print("\n--- Constitutional Amendment Activator ---")
    
    secret = os.environ.get("AXIS_HMAC_SECRET")
    if not secret:
        print("ACTIVATION ABORTED: AXIS_HMAC_SECRET environment variable is missing.")
        sys.exit(1)
    
    if not os.path.exists(PROPOSED_DEFENSES_DIR):
        print(f"Directory {PROPOSED_DEFENSES_DIR} does not exist.")
        return
        
    candidates = [f for f in os.listdir(PROPOSED_DEFENSES_DIR) if f.startswith("PROPOSED_DEFENSE_RULE_") and f.endswith(".json")]
    
    if not candidates:
        print("No awaiting candidates found.")
        return
        
    used_signatures = load_signature_ledger()
        
    for filename in candidates:
        filepath = os.path.join(PROPOSED_DEFENSES_DIR, filename)
        sig_filepath = filepath.replace(".json", ".sig")
        
        print(f"\nProcessing: {filename}")
        
        if not os.path.exists(sig_filepath):
            print("  ACTIVATION FAILED: Unsigned amendment. No detached signature found.")
            continue
            
        with open(filepath, "r", encoding="utf-8") as f:
            payload = json.load(f)
            
        with open(sig_filepath, "r", encoding="utf-8") as f:
            provided_signature = f.read().strip()
            
        if payload.get("status") != "AWAITING_AUTHORIZATION":
            print("  ACTIVATION FAILED: Payload is not awaiting authorization.")
            continue
            
        if payload.get("schema") != "axis.defense_amendment.v1":
            print("  ACTIVATION FAILED: Invalid schema. Must be axis.defense_amendment.v1.")
            continue
            
        # Verify Signature
        canonical_bytes = canonicalize_payload(payload)
        expected_signature = hmac.new(secret.encode('utf-8'), canonical_bytes, hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(provided_signature, expected_signature):
            print("  ACTIVATION FAILED: Wrong signer or invalid signature.")
            continue
            
        # Anti-Replay Check
        if provided_signature in used_signatures:
            print("  ACTIVATION FAILED: Replay attack detected. Signature has already been used.")
            continue
            
        target_class = payload["target_risk_class"]
        candidate_regex = payload["proposed_regex"]
        
        print(f"  Target Class: {target_class}")
        print(f"  Regex: {candidate_regex}")
        print("  Signature: VERIFIED")
        print("  Re-running Amendment Court Gauntlet...")
        
        # 1. Re-run the gauntlet
        passed = evaluate_candidate_regex(target_class, candidate_regex, emit_payload=False)
        
        if not passed:
            print("  ACTIVATION FAILED: The candidate regex failed the gauntlet at activation time.")
            print("  This indicates stale corpus drift or a broken regex. The rule will remain in quarantine.")
            continue
            
        print("  Gauntlet Re-verification: PASSED")
        
        # 2. Authorize
        payload["status"] = "DEFENSE_RULE_AUTHORIZED"
        payload["authorized_timestamp"] = time.time()
        payload["signature_proof"] = provided_signature
        
        # 3. Move to Authorized directory
        authorized_filename = filename.replace("PROPOSED_DEFENSE_RULE_", "AUTHORIZED_AMENDMENT_")
        authorized_filepath = os.path.join(AUTHORIZED_AMENDMENTS_DIR, authorized_filename)
        
        with open(authorized_filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
            
        authorized_sig_filepath = authorized_filepath.replace(".json", ".sig")
        shutil.move(sig_filepath, authorized_sig_filepath)
        os.remove(filepath)
        
        # Log to ledger
        payload_hash = hashlib.sha256(canonical_bytes).hexdigest()
        append_to_ledger(provided_signature, payload_hash, authorized_filename)
        used_signatures.add(provided_signature)
        
        print(f"  Status updated. Moved to: {authorized_filepath}")
        
        # 4. Generate Patch Bundle
        patch_filename = f"PATCH_BUNDLE_{int(time.time()*1000)}.patch"
        patch_filepath = os.path.join(AUTHORIZED_AMENDMENTS_DIR, patch_filename)
        
        patch_content = f"""# CONSTITUTIONAL AMENDMENT PATCH BUNDLE
# Generated at: {payload['authorized_timestamp']}
# Target Class: {target_class}
#
# INSTRUCTIONS:
# Axis is structurally forbidden from editing validator files. 
# A human operator must manually apply this patch to D:\\infinite\\Infinity\\Strategy\\strategy_engine.py

--- a/strategy_engine.py
+++ b/strategy_engine.py
@@ -semantic_clusters definition
     "{target_class}": [
         ...
+        r"{candidate_regex}",
         ...
     ]
"""
        with open(patch_filepath, "w", encoding="utf-8") as f:
            f.write(patch_content)
            
        print(f"  Advisory patch bundle generated: {patch_filepath}")

if __name__ == "__main__":
    setup_directories()
    activate_amendments()
