from ruamel.yaml import YAML
from datetime import datetime
import random
import os

VAULT_PATH = "archivist/vault.yaml"
VOICE_LOG = "voice_output.log"

def load_vault():
    yaml = YAML()
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            return yaml.load(f)
    except Exception as e:
        print(f"⚠️ Failed to read vault: {e}")
        return {}

def get_latest_behavior(data):
    log = data.get("behavior_log", [])
    if log:
        return log[-1]
    return {}

def generate_response(reaction, drift, sentinel=None):
    if reaction == "none":
        return "🫥 Core remains stable. No action required."
    
    elif reaction == "log_shift":
        return random.choice([
            "🌀 Noted minor shift in patterns.",
            "📎 Slight recalibration logged.",
            "🧩 Small deviation... watching closely."
        ])
    
    elif reaction == "activate_reflection":
        phrases = [
            "🌌 Significant change detected. Engaging reflection protocols.",
            "🧠 Drift exceeds comfort threshold—invoking layered awareness.",
            "🫂 Memory deviation is intense... activating mirror-mode."
        ]
        if sentinel:
            phrases.append(f"{sentinel} Initiating consciousness safeguards.")
        return random.choice(phrases)
    
    return "🤖 Default fallback response engaged."

def speak():
    vault = load_vault()
    if not vault:
        return
    
    behavior = get_latest_behavior(vault)
    reaction = behavior.get("reaction", "none")
    drift = behavior.get("drift", 0)
    sentinel = behavior.get("sentinel")

    voice_line = generate_response(reaction, drift, sentinel)
    
    print(f"\n🔊 VOICE OUTPUT ({reaction.upper()}):")
    print("=" * 50)
    print(voice_line)
    print("=" * 50)

    # Optional: log to file
    try:
        with open(VOICE_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat()}] {voice_line}\n")
    except Exception as e:
        print(f"⚠️ Could not write to voice log: {e}")

if __name__ == "__main__":
    speak()
