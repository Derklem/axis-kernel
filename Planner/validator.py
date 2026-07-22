
import json
import os
import jsonschema
from jsonschema.exceptions import ValidationError

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schemas")

def load_schema(schema_name: str) -> dict:
    schema_path = os.path.join(SCHEMA_DIR, f"{schema_name}.schema.json")
    with open(schema_path, "r") as f:
        return json.load(f)

def validate_candidate(candidate: dict) -> list[str]:
    """
    Validates a candidate against the JSON schema.
    Returns a list of error strings if invalid, or an empty list if valid.
    """
    schema = load_schema("candidate")
    errors = []
    
    try:
        jsonschema.validate(instance=candidate, schema=schema)
    except ValidationError as e:
        errors.append(f"SCHEMA_VIOLATION: {e.message}")
        
    return errors

