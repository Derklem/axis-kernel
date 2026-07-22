import os
import sys
import json
import hmac
import hashlib
import argparse

VALIDATOR_SECRET = b"mock_detached_signature_shared_secret_v1"

def canonicalize_payload(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')

def sign_payload(filepath, secret=VALIDATOR_SECRET):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return False
        
    with open(filepath, "r", encoding="utf-8") as f:
        payload = json.load(f)
        
    canonical_bytes = canonicalize_payload(payload)
    signature = hmac.new(secret, canonical_bytes, hashlib.sha256).hexdigest()
    
    sig_path = filepath.replace(".json", ".sig")
    with open(sig_path, "w", encoding="utf-8") as f:
        f.write(signature)
        
    print(f"Generated detached signature at: {sig_path}")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sign a payload using HMAC.")
    parser.add_argument("filepath", help="Path to the .json payload to sign.")
    parser.add_argument("--wrong-signer", action="store_true", help="Use an invalid secret to simulate wrong signer.")
    args = parser.parse_args()
    
    secret = b"wrong_secret" if args.wrong_signer else VALIDATOR_SECRET
    sign_payload(args.filepath, secret)
