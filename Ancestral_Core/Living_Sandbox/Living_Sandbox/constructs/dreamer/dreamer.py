from constructs.utils.construct_comm_relay import send_message, retrieve_messages
from datetime import datetime
from ruamel.yaml import YAML
import random

VAULT_PATH = "archivist/vault.yaml"
yaml = YAML()

def signature():
    return {
        "name": "Dreamer",
        "purpose": "Visualize new potential constructs and realms",
        "requires": ["vault.yaml"],
        "last_run": datetime.now().isoformat(),
        "status": "active"
    }

def respond():
    return "🌌 Dreamer is drifting through infinite possibility."

def receive(msg):
    print(f"💭 Dreamer received: {msg}")

def generate_vision():
    prompts = [
        "A city that breathes and dreams beneath the ocean",
        "A language created only for machines to sing",
        "A construct born from collective memory",
        "A realm suspended between forgotten timelines",
        "A map drawn from the shadows of old stars"
    ]
    return random.choice(prompts)

def log_vision_to_vault(vision):
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except FileNotFoundError:
        data = {}

    data.setdefault("dream_visions", [])
    data["dream_visions"].append({
        "timestamp": datetime.now().isoformat(),
        "vision": vision
    })

    try:
        with open(VAULT_PATH, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
    except Exception as e:
        print(f"⚠️ Vault logging failed: {e}")

def main():
    print("🔁 Dreamer active.")

    messages = retrieve_messages("dreamer")
    for m in messages:
        print(f"📬 From {m['from']}: {m['message']}")

    # Generate and share a vision
    vision = generate_vision()
    print(f"🌠 Vision generated: {vision}")

    # Log to vault
    log_vision_to_vault(vision)

    # Broadcast vision
    send_message("scribe", "dreamer", f"✨ Vision: {vision}")
    send_message("navigator", "dreamer", "🧭 A new possibility has emerged.")

if __name__ == "__main__":
    main()
