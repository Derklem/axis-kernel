import json
from pathlib import Path
from importlib.resources import files
from jsonschema import validate
from laboratory.crypto import canonical_hash

def load_schema(name):
    # Load schema from package data
    schema_text = files("observation.schemas").joinpath(name).read_text(encoding="utf-8")
    return json.loads(schema_text)

def extract_feed(receipt: dict, verification_artifact: dict, artifact_path: str, evaluation_artifact: dict, actual_artifact_hash: str) -> dict:
    validate(instance=receipt, schema=load_schema("observation_input.json"))
    validate(instance=evaluation_artifact, schema=load_schema("evaluation.json"))
    
    # Verify the verification artifact schema manually as we don't have its schema loaded into Observation
    if verification_artifact.get("verification_schema_version") != "1.0.0":
        raise ValueError("Invalid verification artifact version")
        
    if verification_artifact["python_verifier"]["result"] != "PASS":
        return {
            "status": "UNOBSERVABLE",
            "reason_code": "LABORATORY_RUN_NOT_VERIFIED_PYTHON"
        }
        
    if verification_artifact["rust_verifier"]["result"] != "PASS":
        return {
            "status": "UNOBSERVABLE",
            "reason_code": "LABORATORY_RUN_NOT_VERIFIED_RUST"
        }
        
    if not verification_artifact["normalized_reports_equal"]:
        return {
            "status": "UNOBSERVABLE",
            "reason_code": "LABORATORY_REPORTS_MISMATCH"
        }
        
    receipt_hash = canonical_hash(receipt)
    if verification_artifact["receipt_hash"] != receipt_hash:
        return {
            "status": "UNOBSERVABLE",
            "reason_code": "LABORATORY_RECEIPT_MISMATCH"
        }
        
    verification_root = canonical_hash(verification_artifact)
        
    if artifact_path not in receipt["artifacts"]:
        raise ValueError(f"Artifact {artifact_path} not declared in receipt")
        
    expected_hash = receipt["artifacts"][artifact_path]
    if expected_hash != actual_artifact_hash:
        raise ValueError(f"Artifact hash mismatch. Expected {expected_hash}, got {actual_artifact_hash}")
        
    outcome = evaluation_artifact["outcome"]
    if outcome == "SUPPORTED":
        support = 1
    elif outcome == "INCONCLUSIVE":
        support = 0
    elif outcome == "CONTRADICTED":
        support = -1
    else:
        raise ValueError(f"Unknown outcome {outcome}")
        
    subject = evaluation_artifact["subject"]
    receipt_hash = canonical_hash(receipt)
    
    obs_id_input = {
        "receipt_hash": receipt_hash,
        "verification_root": verification_root,
        "artifact_hash": actual_artifact_hash,
        "subject": subject
    }
    obs_id = "OBS_" + canonical_hash(obs_id_input)[:32]
    
    feed = {
        "observation_schema_version": "1.0.0",
        "observations": [
            {
                "observation_id": obs_id,
                "subject": subject,
                "support": support,
                "reason_code": f"EVALUATION_{outcome}",
                "source": {
                    "run_id": receipt["run_id"],
                    "receipt_hash": receipt_hash,
                    "verification_root": verification_root,
                    "artifact_path": artifact_path,
                    "artifact_hash": actual_artifact_hash
                }
            }
        ]
    }
    
    validate(instance=feed, schema=load_schema("observation_feed.json"))
    return feed
