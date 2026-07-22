from constructs.utils.construct_comm_relay import send_message, retrieve_messages

def signature():
    return {
        "name": "Navigator",
        "purpose": "Plot and evaluate possible pathways",
        "requires": ["vault.yaml"],
        "last_run": None,
        "status": "active"
    }

def respond():
    return "🧠 Navigator is aware and responsive."

def receive(msg):
    print(f"📨 Navigator received: {msg}")

def main():
    print("🔁 Navigator active.")

    messages = retrieve_messages("navigator")
    for m in messages:
        sender = m["from"]
        message = m["message"]
        print(f"📬 From {sender}: {message}")

        # Optional dynamic behavior
        if sender == "scribe":
            send_message("dreamer", "navigator", "You may now proceed with imagination.")
        elif sender == "dreamer":
            send_message("navigator", "navigator", "Plot a course through the unknown.")
        elif sender == "navigator":
            send_message("sentinel", "navigator", "Prepare the perimeter.")
        elif sender == "sentinel":
            send_message("scribe", "navigator", "Cycle complete. Chronicle updated.")
