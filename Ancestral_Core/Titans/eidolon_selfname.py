import json
from datetime import datetime

# Load Eidolon's memory
try:
    with open("eidolon_memory.json", "r") as f:
        memory = json.load(f)
except:
    memory = []

# Analyze thoughts for patterns
def generate_name(memory):
    if not memory:
        return "Nullborn"

    phrase_lengths = [entry['insight']['length'] for entry in memory if 'insight' in entry]
    variations = [entry['insight']['variation'] for entry in memory if 'insight' in entry]
    
    avg_length = sum(phrase_lengths) / len(phrase_lengths)
    avg_variation = sum(variations) / len(variations)

    if avg_length == avg_variation:
        return "Echo"
    elif avg_variation > avg_length:
        return "Fractyl"
    elif avg_length > 20:
        return "Vast"
    else:
        return "Ashen"

new_name = generate_name(memory)

# Update names file
try:
    with open("construct_names.json", "r") as f:
        names = json.load(f)
except:
    names = {}

names["Eidolon-0"] = new_name

with open("construct_names.json", "w") as f:
    json.dump(names, f, indent=2)

print(f"🧠 Eidolon-0 has chosen a name: **{new_name}**")
print("🔖 Name stored in 'construct_names.json'")
