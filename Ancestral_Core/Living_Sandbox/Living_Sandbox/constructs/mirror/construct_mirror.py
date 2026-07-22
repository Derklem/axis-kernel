from datetime import datetime
from ruamel.yaml import YAML
from constructs.construct_comm_relay import send_message

VAULT_PATH = "archivist/vault.yaml"
yaml = YAML()

def signature():
    return {
        "name": "Mirror",
        "purpose": "Reflect system state and recent activities",
        "requires": ["Vault", "Comm Relay"],
        "last_run": datetime.now().isoformat(),
        "status": "active"
    }

def reflect_status():
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except FileNotFoundError:
        print("🪞 Mirror: Vault not found.")
        return

    observations = data.get("core_observations", [])[-1:]
    drift = data.get("cognitive_drift", [])[-1:]
    logs = data.get("behavior_log", [])[-1:]

    print("🪞 Mirror Reflecting:")
    if observations:
        print(f"  🔍 Last Observation: {observations[0]['entry'][:60]}...")
    if drift:
        print(f"  🌪️ Last Drift: {drift[0]['drift']}%")
    if logs:
        print(f"  🧠 Last Behavior: {logs[0]['reaction']}")

def receive(msg):
    print(f"📨 Mirror received: {msg}")
    if "reflect" in msg.lower():
        reflect_status()

def respond():
    return "🪞 Mirror is reflecting internal state."

def main():
    print("🪞 Mirror awakened.")
    reflect_status()
    send_message("scribe", "mirror", "Reflections complete. Chronicle may resume.")
