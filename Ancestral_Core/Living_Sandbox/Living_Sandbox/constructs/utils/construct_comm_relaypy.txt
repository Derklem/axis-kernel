# constructs/utils/comm_relay.py

import os
import json

MESSAGE_STORE = "comm_messages.json"

def send_message(to, sender, message):
    if not os.path.exists(MESSAGE_STORE):
        with open(MESSAGE_STORE, "w") as f:
            json.dump([], f)

    with open(MESSAGE_STORE, "r") as f:
        all_messages = json.load(f)

    all_messages.append({
        "to": to,
        "from": sender,
        "message": message
    })

    with open(MESSAGE_STORE, "w") as f:
        json.dump(all_messages, f, indent=2)

def retrieve_messages(construct_name):
    if not os.path.exists(MESSAGE_STORE):
        return []

    with open(MESSAGE_STORE, "r") as f:
        all_messages = json.load(f)

    messages = [m for m in all_messages if m["to"] == construct_name]

    # Remove retrieved messages
    remaining = [m for m in all_messages if m not in messages]
    with open(MESSAGE_STORE, "w") as f:
        json.dump(remaining, f, indent=2)

    return messages
