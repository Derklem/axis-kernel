
def normalize_candidate(candidate: dict) -> dict:
    """
    Normalizes a candidate dictionary to reduce accidental nondeterminism.
    - Trims whitespace from string values
    - Sorts dependencies and constraints alphabetically
    - Ensures standard casing for enums
    """
    normalized = {}
    
    # Sort keys alphabetically for predictable serialization
    for key in sorted(candidate.keys()):
        val = candidate[key]
        
        if isinstance(val, str):
            val = val.strip()
            # Normalize enum casing
            if key in ("risk_level",):
                val = val.upper()
            if key in ("execution_mode", "status"):
                val = val.lower()
        elif isinstance(val, list) and key in ("dependencies", "constraints", "source_refs"):
            # Sort arrays that are conceptually sets
            val = sorted([v.strip() if isinstance(v, str) else v for v in val])
            
        normalized[key] = val
        
    return normalized

