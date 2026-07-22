import json
import os
import hashlib
import jsonschema

POLICY_DIR = os.path.join(os.path.dirname(__file__), "policies")
SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schemas")

def load_policy(policy_id: str, policy_dir_override: str = None) -> dict:
    """Loads a policy by ID, validating it against the schema, returning the parsed JSON dictionary."""
    base_dir = policy_dir_override if policy_dir_override else POLICY_DIR
    policy_path = os.path.join(base_dir, f"{policy_id}.json")
    with open(policy_path, "r") as f:
        policy = json.load(f)
        
    schema_path = os.path.join(SCHEMA_DIR, "policy.schema.json")
    with open(schema_path, "r") as f:
        schema = json.load(f)
        
    jsonschema.validate(instance=policy, schema=schema)
    return policy

def hash_dict(d: dict) -> str:
    """Computes a stable SHA-256 hash of a dictionary."""
    canonical_json = json.dumps(d, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

def get_policy_hash(policy_id: str, policy_dir_override: str = None) -> str:
    policy = load_policy(policy_id, policy_dir_override)
    return hash_dict(policy)

def get_schema_hash(policy_id: str, policy_dir_override: str = None) -> str:
    """Combines all schemas and the policy into a named manifest and returns its hash."""
    manifest = {}
    for name in ["candidate", "agenda", "decision_receipt", "policy"]:
        schema_path = os.path.join(SCHEMA_DIR, f"{name}.schema.json")
        with open(schema_path, "r") as f:
            # Parse and hash canonical JSON, not raw file string
            manifest[name] = hash_dict(json.load(f))
            
    manifest["active_policy"] = get_policy_hash(policy_id, policy_dir_override)
    return hash_dict(manifest)
