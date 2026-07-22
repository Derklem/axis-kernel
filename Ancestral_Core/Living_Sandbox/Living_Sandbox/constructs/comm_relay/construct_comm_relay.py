# constructs/construct_comm_relay.py

from datetime import datetime
from ruamel.yaml import YAML
import os

VAULT_PATH = "archivist/vault.yaml"
yaml = YAML()

def send_message(to, sender, message):
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except FileNotFoundError:
        data = {}

    data.setdefault("construct_messages", [])

    data["construct_messages"].append({
        "timestamp": datetime.now().isoformat(),
        "from": sender,
        "to": to,
        "message": message
    })

    with open(VAULT_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

def retrieve_messages(construct_name):
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except FileNotFoundError:
        return []

    messages = data.get("construct_messages", [])
    return [m for m in messages if m.get("to") == construct_name]
