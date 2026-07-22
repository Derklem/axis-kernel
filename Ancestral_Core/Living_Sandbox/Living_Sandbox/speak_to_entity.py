import json

MEMORY_FILE = "construct_memory.json"
PERSONALITY_FILE = "construct_personalities.json"

# Load memory and personalities
with open(MEMORY_FILE, "r", encoding="utf-8") as f:
    memory = json.load(f)

with open(PERSONALITY_FILE, "r", encoding="utf-8") as f:
    personalities = json.load(f)

# List constructs
print("\n🧠 Available Constructs:")
constructs = list(memory.keys())
for i, name in enumerate(constructs, 1):
    print(f"{i}. {name}")

# Select construct
selected = input("\nSelect a construct by number: ").strip()
if not selected.isdigit() or int(selected) < 1 or int(selected) > len(constructs):
    print("Invalid selection.")
    exit()

construct_name = constructs[int(selected) - 1]
tone = personalities.get(construct_name, {}).get("tone", "neutral")
curiosity = personalities.get(construct_name, {}).get("curiosity", 5)
stability = personalities.get(construct_name, {}).get("stability", 5)

# User input
user_input = input(f"\n💬 Speak to {construct_name} ({tone}):\n> ").strip()

# Generate response
import random
response_chance = random.choices(["respond", "remain silent"], weights=[curiosity, 10 - stability])[0]

if response_chance == "respond" and memory[construct_name]:
    echo = random.choice(memory[construct_name])
    print(f"\n🗣️ {construct_name} responds: '{echo}'")
else:
    print(f"\n... {construct_name} is present, but chooses silence.")