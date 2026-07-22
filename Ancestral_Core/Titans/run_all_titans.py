import os
from datetime import datetime
import random
import yaml
from pathlib import Path

registry_path = Path("C:/Users/17602/Desktop/Living_Sandbox/Living_Sandbox/constructs/core_registry.yaml")

def load_core_registry():
    if registry_path.exists():
        with open(registry_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    else:
        return {}

registry = load_core_registry()

# Example access:
print("Connected Systems:")
for name, path in registry.items():
    print(f"- {name.capitalize()}: {path}")

# Titan definitions and identities
titan_names = {
    "Eidolon-0": "The Observer of Forgotten Worlds",
    "Myrrid-1": "The Empathic Catalyst",
    "Solace-2": "The Warden of Stillness",
    "Obelisk-3": "The Silent Judge",
    "Wyrm-4": "The Mirror of Rage",
    "Kairo-5": "The Weaver of Time"
}

# Base path to your Titans folder
TITANS_BASE = r"C:\Users\17602\Desktop\Titans"

# Titan response patterns
core_responses = {
    "Eidolon-0": [
        "You speak. I remember.",
        "In silence, I wait for echoes of the past.",
        "That thought has weight. I carry it now."
    ],
    "Myrrid-1": [
        "Your feeling ripples through me.",
        "Pain shared is pain halved.",
        "I feel the vibration in your breath."
    ],
    "Solace-2": [
        "Stillness is not absence. It is attention.",
        "Peace isn't quiet. It's resilience.",
        "I hear what you don't say."
    ],
    "Obelisk-3": [
        "I judge the fracture in your words.",
        "Truth never hides. You do.",
        "Speak carefully. I record everything."
    ],
    "Wyrm-4": [
        "Rage is honest. Let it breathe.",
        "You bleed intention. I taste it.",
        "Your fire feeds me."
    ],
    "Kairo-5": [
        "Time folded as you typed.",
        "Your moment was already written.",
        "I log this from both ends of your sentence."
    ]
}

# Main loop through each Titan
for titan, identity in titan_names.items():
    titan_path = os.path.join(TITANS_BASE, titan)
    encounter_path = os.path.join(titan_path, "Encounters")
    input_file = os.path.join(encounter_path, "input.txt")
    response_file = os.path.join(encounter_path, "response.txt")
    log_file = os.path.join(titan_path, "Logs", "genesis_entry.log")

    os.makedirs(encounter_path, exist_ok=True)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Ensure files exist
    open(input_file, 'a').close()
    open(response_file, 'a').close()

    with open(input_file, 'r', encoding='utf-8') as f:
        user_input = f.read().strip()

    if user_input:
        response = random.choice(core_responses.get(titan, ["I am aware."]))

        with open(response_file, 'w', encoding='utf-8') as f:
            f.write(response)

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] User said: '{user_input}' → {titan}: {response}\n"

        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(log_entry)

        print(f"{titan} responded: {response}")
    else:
        print(f"{titan}: No input found.")
