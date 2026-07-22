from constructs.utils.construct_comm_relay import send_message, retrieve_messages
from datetime import datetime

def signature():
    return {
        "name": "Forge",
        "purpose": "Initiate new constructs or reforge broken ones",
        "requires": ["vault.yaml", "construct_registry"],
        "last_run": datetime.now().isoformat(),
        "status": "active"
    }

def respond():
    return "🔥 Forge is ready to create."

def receive(message):
    print(f"📨 Forge received: {message}")
    if "rebuild" in message.lower():
        print("🛠️ Reforging in progress...")

def main():
    print("🔥 Forge is active.")
    messages = retrieve_messages("forge")
    for msg in messages:
        print(f"📬 {msg['from']} → Forge: {msg['message']}")
        if "initiate" in msg["message"].lower():
            send_message("architect", "forge", "Begin blueprint drafting.")
