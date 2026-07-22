def check_eligibility(candidate: dict, constraints: dict, existing_candidate_ids: set) -> list[str]:
    """
    Evaluates business/domain eligibility rules.
    Returns a list of rejection reasons. If empty, the candidate is ELIGIBLE.
    """
    reasons = []

    # 1. Duplicate detection
    if candidate.get("candidate_id") in existing_candidate_ids:
        reasons.append("DUPLICATE_CANDIDATE")

    # 2. Dependency resolution
    # (Assuming constraints["resolved_dependencies"] contains available ones)
    resolved_deps = constraints.get("resolved_dependencies", set())
    for dep in candidate.get("dependencies", []):
        if dep not in resolved_deps:
            reasons.append(f"UNRESOLVED_DEPENDENCY:{dep}")

    # 3. Budget limits
    max_compute = constraints.get("max_compute_minutes", float("inf"))
    if candidate.get("estimated_compute_minutes", 0) > max_compute:
        reasons.append("COMPUTE_BUDGET_EXCEEDED")

    # 4. Prohibited state check
    if candidate.get("risk_level") == "BLACK":
        reasons.append("PROHIBITED_RISK_LEVEL")

    return reasons
