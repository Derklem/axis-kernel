def score_candidate(candidate: dict, policy: dict) -> dict:
    """
    Deterministically scores an eligible candidate using the provided policy.
    Returns a dictionary containing the final priority_score and the score_breakdown.
    """
    weights = policy.get("weights", {})
    attention_mapping = policy.get("attention_cost_mapping", {})
    risk_mapping = policy.get("risk_penalty", {})

    # Extract base values
    ig = candidate.get("expected_information_gain", 0.0)
    age = candidate.get("epistemic_debt_age_hours", 0.0)
    compute = candidate.get("estimated_compute_minutes", 0.0)
    
    # Map qualitative strings to numeric
    attention_str = candidate.get("attention_cost", "acceptable")
    attention_val = attention_mapping.get(attention_str, attention_mapping.get("acceptable", 5.0))
    
    risk_str = candidate.get("risk_level", "GREEN")
    risk_val = risk_mapping.get(risk_str, 0.0)

    # Compute breakdown components
    breakdown = {
        "information_gain": ig * weights.get("information_gain", 1.0),
        "epistemic_debt_age_hours": age * weights.get("epistemic_debt_age_hours", 1.0),
        "attention_cost": attention_val * weights.get("attention_cost", -1.0),
        "estimated_compute_minutes": compute * weights.get("estimated_compute_minutes", -1.0),
        "risk_penalty": risk_val * weights.get("risk_penalty", -1.0)
    }

    priority_score = sum(breakdown.values())

    return {
        "priority_score": priority_score,
        "score_breakdown": breakdown
    }
