def signature():
    return {
        "name": "Navigator",
        "purpose": "Scan paths and determine next steps",
        "requires": ['Architect', 'Map module'],
        "last_run": None,
        "status": "active"
    }

def respond():
    return "⚙️ No default response set."

def receive(message):
    print(f"📨 Received message: {message}")
