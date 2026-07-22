import json
import random

VOICE_FILE = "constructs/identity_profiles.json"

def load_voices():
    with open(VOICE_FILE, "r", encoding="utf-8") as f:
        profiles = json.load(f)
    return profiles

def select_voice(context="default"):
    profiles = load_voices()
    context_voices = profiles.get(context, profiles.get("default", []))
    if not context_voices:
        print("[VOICE SELECTOR] No voices found for context.")
        return None
    chosen = random.choice(context_voices)
    print(f"[VOICE SELECTOR] Voice selected: {chosen['name']} ({chosen['tone']})")
    return chosen
