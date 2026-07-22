def signature():
    return {
        "name": "Voice",
        "purpose": "Handle routing and communication",
        "requires": ['Comm_Relay'],
        "last_run": None,
        "status": "active"
    }

def respond():
    return "⚙️ No default response set."

def receive(message):
    print(f"📨 Received message: {message}")
