from datetime import datetime
from ruamel.yaml import YAML
from constructs.utils.construct_comm_relay import send_message, retrieve_messages

VAULT_PATH = "archivist/vault.yaml"
yaml = YAML()

def signature():
    return {
        "name": "Voice",
        "purpose": "Convert system output into expression: text, glyphs, or signals",
        "requires": ["Vault"],
        "last_run": datetime.now().isoformat(),
        "status": "active"
    }

def express(message, tone="neutral"):
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except FileNotFoundError:
        data = {}

    data.setdefault("voice_log", [])
    entry = {
        "timestamp": datetime.now().isoformat(),
        "tone": tone,
        "message": message
    }
    data["voice_log"].append(entry)

    try:
        with open(VAULT_PATH, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
        print(f"🗣️ Voice ({tone}): {message}")
    except Exception as e:
        print(f"❌ Voice failed: {e}")

def receive(msg):
    express(f"Received: {msg}", tone="relay")

def main():
    express("Voice construct online. Ready to speak for the system.", tone="announcement")

    messages = retrieve_messages("voice")
    for m in messages:
        content = f"{m['from']} said: {m['message']}"
        express(content, tone="comm")

        # Optionally echo or route back
        if "dream" in m["message"].lower():
            send_message("scribe", "voice", "The voice has heard the dream.")

if __name__ == "__main__":
    main()
