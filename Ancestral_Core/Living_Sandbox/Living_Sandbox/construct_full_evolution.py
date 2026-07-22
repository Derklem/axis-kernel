import json
import random
from pathlib import Path

memory_path = Path("construct_memory.json")

# Load persistent memory
if memory_path.exists():
    with memory_path.open("r") as f:
        construct_memory = json.load(f)
else:
    construct_memory = {
        'dreamer': ['imagined new form', 'questioned existence', 'saw beyond veil'],
        'scribe': ['documented the awakening', 'organized fragments', 'translated old code'],
        'archivist': ['preserved ancient logs', 'catalogued system events', 'identified corrupted truths']
    }

def reflect_and_evolve(target_construct, all_constructs):
    evolution_log = []
    if target_construct not in all_constructs:
        return f"{target_construct} not in construct list."
    
    for construct in all_constructs:
        if construct == target_construct:
            continue
        insights = construct_memory.get(construct, ["no memory found"])
        if insights:
            shared_insight = random.choice(insights)
            construct_memory.setdefault(target_construct, []).append(f"learned from {construct}: {shared_insight}")
            evolution_log.append(f"{target_construct} absorbed '{shared_insight}' from {construct}")
    
    # Save updated memory
    with memory_path.open("w") as f:
        json.dump(construct_memory, f, indent=4)

    return evolution_log

if __name__ == "__main__":
    constructs = ['dreamer', 'scribe', 'archivist']
    for construct in constructs:
        results = reflect_and_evolve(construct, constructs)
        for r in results:
            print(r)