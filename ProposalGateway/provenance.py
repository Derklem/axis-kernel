def verify_provenance(candidate: dict, source_context: dict) -> bool:
    """
    Ensures the candidate has valid source_refs tied to the context.
    """
    refs = candidate.get("source_refs", [])
    if not refs:
        return False
        
    allowed_refs = source_context.get("allowed_source_refs", set())
    for ref in refs:
        if ref not in allowed_refs:
            return False
            
    return True
