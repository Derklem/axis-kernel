
import json
import os
from pathlib import Path
import random
from construct_memory import remember, recall

VEIL_PATH = Path(__file__).resolve().parent / "personality" / "veils"

def load_veil(construct_name):
    path = VEIL_PATH / f"{construct_name}.json"
    if not path.exists():
        print(f"No veil found for: {construct_name}")
        return None
    with open(path, 'r') as f:
        return json.load(f)

def simulate_response(veil, user_input):
    tone = veil.get("tone", "neutral")
    quirks = veil.get("quirks", [])
    domain = veil.get("domain", "undefined")

    style_note = f"({tone.upper()} | Domain: {domain})"
    quirk = random.choice(quirks) if quirks else ""

    response = f"'{user_input}'... hmm. That reminds me of something. {quirk.capitalize() if quirk else ''}"
    return f"[{style_note}] {response}"

def main():
    print("🌀 Halcyon Construct Dialogue Interface + Memory")
    print("Type 'exit' at any time to quit.\n")

    while True:
        construct = input("Which construct would you like to speak to? >> ").strip().lower()
        if construct == "exit":
            break

        veil = load_veil(construct)
        if not veil:
            continue

        print(f"Connected to {construct.capitalize()}. Recalling memory...\n")
        recent_memory = recall(construct)
        for line in recent_memory:
            print(f"{line}")
        print("\nBegin your conversation.")

        while True:
            user_input = input(f"You > ").strip()
            if user_input.lower() in ["exit", "back"]:
                print(f"Disconnecting from {construct}...\n")
                break
            response = simulate_response(veil, user_input)
            print(f"{construct.capitalize()} > {response}\n")
            remember(construct, user_input, response)

if __name__ == "__main__":
    main()
