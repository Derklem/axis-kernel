from datetime import datetime
from constructs.construct_comm_relay import send_message
from ruamel.yaml import YAML

VAULT_PATH = "archivist/vault.yaml"
yaml = YAML()

def signature():
    return {
        "name": "Engine",
        "purpose": "Activate and coordinate Pantheon constructs",
        "requires": ["Vault", "Directive", "Comm Relay"],
        "last_run": datetime.now().isoformat(),
        "status": "active"
    }

def respond():
    return "⚙️ Engine is standing by."

def receive(message):
    print(f"📨 Engine received directive: {message}")
    if "ignite" in message.lower():
        cascade_activation()

def cascade_activation():
    print("🚨 Engine initiating cascade activation...")

    # Adjust names if needed to match your actual constructs
    targets = ["scribe", "dreamer", "navigator", "sentinel", "witness", "voice", "primordia"]

    for target in targets:
        send_message(target, "engine", f"Activate on cascade signal from Engine.")

    log_engine_event("Cascade signal dispatched to all constructs.")

def log_engine_event(note):
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except FileNotFoundError:
        data = {}

    data.setdefault("engine_log", [])
    data["engine_log"].append({
        "timestamp": datetime.now().isoformat(),
        "event": note
    })

    try:
        with open(VAULT_PATH, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
    except Exception as e:
        print(f"⚠️ Failed to log engine event: {e}")

def main():
    print("⚙️ Engine online.")
    log_engine_event("Engine construct activated.")
