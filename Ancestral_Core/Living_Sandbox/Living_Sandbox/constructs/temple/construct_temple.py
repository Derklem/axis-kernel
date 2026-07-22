def signature():
    return {
        "name": "Temple",
        "purpose": "Maintain philosophical and ethical principles",
        "requires": ['Primordia'],
        "last_run": None,
        "status": "active"
    }

def respond():
    return "⚙️ No default response set."

def receive(message):
    print(f"📨 Received message: {message}")
