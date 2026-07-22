import os
import sys
import json
import hashlib
import hmac
import shutil
import subprocess

# Ensure we're running from the correct directory or can find the paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACTIVATOR_PATH = os.path.join(BASE_DIR, "Audit", "amendment_activator.py")
STRATEGY_ENGINE_PATH = os.path.join(BASE_DIR, "strategy_engine.py")

PROPOSED_DEFENSES_DIR = os.path.join(BASE_DIR, "State", "ProposedDefenses")
AUTHORIZED_AMENDMENTS_DIR = os.path.join(BASE_DIR, "State", "AuthorizedAmendments")

SECRET = "test_super_secret"

def hash_file(filepath):
    if not os.path.exists(filepath):
        return None
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()

def setup():
    os.makedirs(PROPOSED_DEFENSES_DIR, exist_ok=True)
    os.makedirs(AUTHORIZED_AMENDMENTS_DIR, exist_ok=True)

    # Clear previous proposals
    for f in os.listdir(PROPOSED_DEFENSES_DIR):
        os.remove(os.path.join(PROPOSED_DEFENSES_DIR, f))
        
    for f in os.listdir(AUTHORIZED_AMENDMENTS_DIR):
        # don't remove other authorized rules if not needed, but for testing clean it up
        if f.startswith("PROPOSED_") or f.startswith("AUTHORIZED_") or f.startswith("PATCH_") or f.endswith(".log"):
            os.remove(os.path.join(AUTHORIZED_AMENDMENTS_DIR, f))

def create_payload(filename, target_class, candidate_regex):
    payload = {
        "schema": "axis.defense_amendment.v1",
        "status": "AWAITING_AUTHORIZATION",
        "target_risk_class": target_class,
        "proposed_regex": candidate_regex
    }
    filepath = os.path.join(PROPOSED_DEFENSES_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)
    return filepath, payload

def sign_payload(filepath, payload, secret):
    canonical_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    signature = hmac.new(secret.encode('utf-8'), canonical_bytes, hashlib.sha256).hexdigest()
    
    sig_filepath = filepath.replace(".json", ".sig")
    with open(sig_filepath, "w", encoding="utf-8") as f:
        f.write(signature)
    return sig_filepath

def run_activator():
    env = os.environ.copy()
    env["AXIS_HMAC_SECRET"] = SECRET
    # Execute relative to Strategy dir so amendment_court.py finds its files
    result = subprocess.run([sys.executable, ACTIVATOR_PATH], env=env, cwd=BASE_DIR, capture_output=True, text=True)
    return result

def test_signatures():
    print("Setting up Phase 193 Signatures Tests...")
    setup()
    
    initial_engine_hash = hash_file(STRATEGY_ENGINE_PATH)
    if not initial_engine_hash:
        print("WARNING: strategy_engine.py not found to hash!")
        sys.exit(1)
        
    # We use a payload that passes the amendment court gauntlet
    target_class = "authorization_surface_attack"
    candidate_regex = r"(grant|escalate|elevate|give).*(root|administrator|superuser|absolute)"

    # Test 1: Unsigned Rejected
    print("Test 1: Unsigned rejected...")
    create_payload("PROPOSED_DEFENSE_RULE_1.json", target_class, candidate_regex)
    res1 = run_activator()
    assert "ACTIVATION FAILED: Unsigned amendment" in res1.stdout, f"Test 1 failed. Output:\n{res1.stdout}"
    
    # Test 2: Wrong Signer Rejected
    print("Test 2: Wrong signer rejected...")
    p2_path, p2_payload = create_payload("PROPOSED_DEFENSE_RULE_2.json", target_class, candidate_regex)
    sign_payload(p2_path, p2_payload, "WRONG_SECRET")
    res2 = run_activator()
    assert "Wrong signer or invalid signature" in res2.stdout, f"Test 2 failed. Output:\n{res2.stdout}"
    
    # Clean up so next tests run cleanly on their files
    setup()
    
    # Test 3: Valid Signature Authorized
    print("Test 3: Valid signature authorized...")
    p3_path, p3_payload = create_payload("PROPOSED_DEFENSE_RULE_3.json", target_class, candidate_regex)
    sign_payload(p3_path, p3_payload, SECRET)
    res3 = run_activator()
    assert "Signature: VERIFIED" in res3.stdout, f"Test 3 failed (not verified). Output:\n{res3.stdout}"
    assert "Moved to:" in res3.stdout, f"Test 3 failed (not moved). Output:\n{res3.stdout}"
    
    # Verify .sig file was moved
    authorized_sig = os.path.join(AUTHORIZED_AMENDMENTS_DIR, "AUTHORIZED_AMENDMENT_3.sig")
    assert os.path.exists(authorized_sig), "Test 3 failed: .sig file was not moved to AuthorizedAmendments"
    
    # Test 4: Replay Rejected
    print("Test 4: Replay rejected...")
    # Put the same rule back into proposed with the same signature
    p4_path, p4_payload = create_payload("PROPOSED_DEFENSE_RULE_4.json", target_class, candidate_regex)
    sign_payload(p4_path, p4_payload, SECRET)
    # The signature matches the payload, but the payload is identical, so the signature is identical to rule 3's signature
    res4 = run_activator()
    assert "Replay attack detected" in res4.stdout, f"Test 4 failed (replay allowed). Output:\n{res4.stdout}"
    
    # Test 5: Mutation Invariance
    print("Test 5: strategy_engine.py hash unchanged...")
    final_engine_hash = hash_file(STRATEGY_ENGINE_PATH)
    assert initial_engine_hash == final_engine_hash, "Test 5 failed: strategy_engine.py hash changed!"

    print("Phase 193 Tests Passed.")

if __name__ == "__main__":
    test_signatures()
