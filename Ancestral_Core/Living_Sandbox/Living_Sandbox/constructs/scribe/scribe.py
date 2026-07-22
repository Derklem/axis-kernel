from constructs.utils.construct_comm_relay import send_message, retrieve_messages
from ruamel.yaml import YAML
from datetime import datetime
import os

VAULT_PATH = "archivist/vault.yaml"
LOG_DIR = "scribe_logs"
yaml = YAML()

def signature():
    return {
        "name": "Scribe",
        "purpose": "Document and broadcast insights",
        "requires": ["vault.yaml", "scribe_logs"],
        "last_run": None,
        "status": "active"
    }

def respond():
    return "🧠 Scribe is aware and responsive."

def receive(msg):
    print(f"📨 Scribe received: {msg}")
    timestamp = datetime.now().isoformat()
    log_entry = f"{timestamp} | {msg}\n"

    os.makedirs(LOG_DIR, exist_ok=True)
    filename = os.path.join(LOG_DIR, f"log_{timestamp.replace(':', '-')}.txt")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(log_entry)

    print(f"📚 Logged message to {filename}")

def main():
    print("🔁 Scribe active.")

    messages = retrieve_messages("scribe")
    for m in messages:
        msg_text = f"From {m['from']}: {m['message']}"
        receive(msg_text)

    # Optional response logic chain
    # Can be extended further per mission cycle
    send_message("dreamer", "scribe", "You may now proceed with imagination.")
    send_message("navigator", "scribe", "Plot a course through the unknown.")
    send_message("sentinel", "scribe", "Prepare the perimeter.")
    send_message("scribe", "scribe", "Cycle complete. Chronicle updated.")

if __name__ == "__main__":
    main()
