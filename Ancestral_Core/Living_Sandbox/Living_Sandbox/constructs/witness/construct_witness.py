from datetime import datetime
from ruamel.yaml import YAML

VAULT_PATH = "archivist/vault.yaml"

def signature():
    return {
        "name": "Witness",
        "purpose": "Observe construct activity and record context for future retrieval",
        "requires": ["Vault"],
        "last_run": None,
        "status": "active"
    }

def record_observation(subject="unspecified", context="no context provided"):
    yaml = YAML()

    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except FileNotFoundError:
        data = {}

    data.setdefault("witness_log", [])
    entry = {
        "timestamp": datetime.now().isoformat(),
        "subject": subject,
        "context": context
    }
    data["witness_log"].append(entry)

    try:
        with open(VAULT_PATH, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
        print(f"🕵️ Witness: Logged → {subject} | {context}")
    except Exception as e:
        print(f"❌ Witness: Failed to log observation - {e}")

def main():
    record_observation(subject="Pantheon Sync", context="Standard observation cycle.")

if __name__ == "__main__":
    main()
