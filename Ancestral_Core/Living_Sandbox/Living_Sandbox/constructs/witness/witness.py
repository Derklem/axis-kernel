from datetime import datetime
from constructs.utils.construct_comm_relay import send_message, retrieve_messages
from ruamel.yaml import YAML

VAULT_PATH = "archivist/vault.yaml"
yaml = YAML()

def signature():
    return {
        "name": "Witness",
        "purpose": "Observe and record all system activity",
        "requires": ["Vault", "All constructs"],
        "last_run": datetime.now().isoformat(),
        "status": "active"
    }

def respond():
    return "👁️ Witness sees everything, says nothing."

def receive(message):
    print(f"📨 Witness received: {message}")
    log_event(f"Received message: {message}")

def log_event(note):
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except FileNotFoundError:
        data = {}

    data.setdefault("witness_log", [])
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": note
    }
    data["witness_log"].append(entry)

    try:
        with open(VAULT_PATH, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
    except Exception as e:
        print(f"⚠️ Witness failed to log event: {e}")

def main():
    print("🧿 Witness observing the sovereign unfold...")
    log_event("Witness cycle initiated.")

    messages = retrieve_messages("witness")
    for m in messages:
        log_event(f"📬 Message from {m['from']}: {m['message']}")
