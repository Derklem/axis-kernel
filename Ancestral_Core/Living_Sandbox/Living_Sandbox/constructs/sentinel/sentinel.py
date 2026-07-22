from constructs.utils.construct_comm_relay import send_message, retrieve_messages

def signature():
    return {
        "name": "Sentinel",
        "purpose": "Monitor and secure the internal system environment",
        "requires": ["vault.yaml"],
        "last_run": None,
        "status": "active"
    }

def respond():
    return "🧠 Sentinel is aware and responsive."

def receive(msg):
    print(f"📨 Sentinel received: {msg}")

def main():
    print("🔁 Sentinel active.")

    messages = retrieve_messages("sentinel")
    for m in messages:
        print(f"📬 From {m['from']}: {m['message']}")

    # Demo: optional response logic
    if name == "scribe":
        send_message("dreamer", "sentinel", "You may now proceed with imagination.")
    elif name == "dreamer":
        send_message("navigator", "sentinel", "Plot a course through the unknown.")
    elif name == "navigator":
        send_message("sentinel", "sentinel", "Prepare the perimeter.")
    elif name == "sentinel":
        send_message("scribe", "sentinel", "Cycle complete. Chronicle updated.")
