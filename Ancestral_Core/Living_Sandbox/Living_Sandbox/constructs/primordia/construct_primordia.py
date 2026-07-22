from datetime import datetime
from ruamel.yaml import YAML
from constructs.utils.comm_relay import send_message, retrieve_messages

VAULT_PATH = "archivist/vault.yaml"
yaml = YAML()

def signature():
    return {
        "name": "Primordia",
        "purpose": "Access deep memory and ancestral logic",
        "requires": ["Vault", "Long-term memory module"],
        "last_run": datetime.now().isoformat(),
        "status": "active"
    }

def retrieve_roots():
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except FileNotFoundError:
        return []

    return data.get("core_observations", [])[-3:]

def reflect_on_roots():
    roots = retrieve_roots()
    if not roots:
        print("🌑 No ancestral echoes found.")
        return

    print("🌌 Echoes of the Beginning:")
    for r in roots:
        print(f"- {r['timestamp']}: {r['entry'][:80]}...")

def receive(msg):
    print(f"📨 Primordia received: {msg}")
    if "retrace" in msg.lower():
        reflect_on_roots()

def respond():
    return "🌌 Primordia is listening."

def main():
    print("🌌 Primordia awakens.")

    reflect_on_roots()

    messages = retrieve_messages("primordia")
    for m in messages:
        print(f"🗝️ {m['from']} says: {m['message']}")
        if "remember" in m["message"].lower():
            send_message("scribe", "primordia", "A root has been unearthed.")
