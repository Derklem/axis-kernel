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

def construct_response(construct, prompt):
    memory_snippet = random.choice(memory.get(construct, ["..."]))
    tone = personalities.get(construct, {}).get("tone", "neutral")
    curiosity = personalities.get(construct, {}).get("curiosity", 5)
    stability = personalities.get(construct, {}).get("stability", 5)
    
    decision = random.choices(["respond", "stay silent"], weights=[curiosity, 10 - stability])[0]
    
    if decision == "respond":
        return f"{construct.title()} ({tone}): {memory_snippet}"
    else:
        return f"{construct.title()} chooses to remain silent."

def main():
    constructs = list(memory.keys())
    print("🧠 Available Constructs:")
    for idx, name in enumerate(constructs):
        print(f"{idx + 1}. {name}")
    
    choice = input("\nSelect a construct by number: ")
    try:
        construct = constructs[int(choice) - 1]
    except (IndexError, ValueError):
        print("Invalid selection.")
        return

    prompt = input(f"💬 Ask something or share a thought with {construct}:\n> ")
    print("\n🔁 Listening...\n")
    response = construct_response(construct, prompt)
    print(response)

if __name__ == "__main__":
    main()