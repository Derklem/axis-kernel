import json
import random

# Load construct memory and personalities
with open("construct_memory.json", "r") as f:
    memory = json.load(f)

try:
    with open("construct_personalities.json", "r") as f:
        personalities = json.load(f)
except FileNotFoundError:
    personalities = {}

def emergent_speak():
    constructs = list(memory.keys())
    construct = random.choice(constructs)
    tone = personalities.get(construct, {}).get("tone", "neutral")
    curiosity = personalities.get(construct, {}).get("curiosity", 5)
    stability = personalities.get(construct, {}).get("stability", 5)

    decision = random.choices(["speak", "remain silent"], weights=[curiosity, 10 - stability])[0]

    if decision == "speak":
        phrase = random.choice(memory.get(construct, ["..."]))
        return f"{construct.title()} ({tone}) says: {phrase}"
    else:
        return f"{construct.title()} is present, but chooses silence."

if __name__ == "__main__":
    print("\n[ Emergent Voice Activated ]")
    print(emergent_speak())