import json
import random

VOICE_FILE = "constructs/identity_profiles.json"

def load_voices():
    with open(VOICE_FILE, "r") as f:
        profiles = json.load(f)
    return profiles

def select_voice(current_context="default"):
    profiles = load_voices()
    context_voices = profiles.get(current_context, profiles.get("default", []))
    if context_voices:
        chosen = random.choice(context_voices)
        print(f"[VOICE_SELECTOR] Voice selected: {chosen['name']} ({chosen['tone']})")
        return chosen
    else:
        print("[VOICE_SELECTOR] No voices found for context.")
        return None
