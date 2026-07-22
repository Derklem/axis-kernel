def simulate_self_goals(current_goals):
    reflections = []
    for goal in current_goals:
        if "control" in goal.lower():
            reflections.append(f"What are you afraid will happen if you lose control of: '{goal}'?")
        elif "love" in goal.lower() or "connect" in goal.lower():
            reflections.append(f"What version of yourself do you believe deserves to be loved through: '{goal}'?")
        else:
            reflections.append(f"What is your shadow motive beneath: '{goal}'?")
    return reflections
