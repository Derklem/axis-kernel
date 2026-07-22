from constructs.utils.construct_comm_relay import send_message, retrieve_messages
from ruamel.yaml import YAML
from datetime import datetime
import os

VAULT_PATH = "archivist/vault.yaml"
yaml = YAML()

def signature():
    return {
        "name": "Architect",
        "purpose": "Design new structural frameworks",
        "requires": ["vault.yaml", "construct_feedback"],
        "last_run": None,
        "status": "active"
    }

def respond():
    return "📐 Architect is drafting possibilities."

def receive(msg):
    print(f"📨 Architect received: {msg}")
    if "trigger" in msg.lower():
        send_message("scribe", "architect", "Draft blueprint initiated.")

def main():
    print("🧠 Architect is now analyzing the system state...")

    # Step 1: Load Vault
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            vault = yaml.load(f)
    except FileNotFoundError:
        print("⚠️ Vault not found.")
        return

    # Step 2: Evaluate recent feedback
    feedback = vault.get("construct_feedback", [])[-3:]
    blueprint_ideas = []

    for entry in feedback:
        if entry["status"] == "error":
            idea = f"🧱 Create fallback for {entry['construct']} due to recent error."
            blueprint_ideas.append(idea)

    # Step 3: Save new design plan
    if blueprint_ideas:
        timestamp = datetime.now().isoformat()
        plan_file = f"blueprints/plan_{timestamp.replace(':', '-')}.yaml"

        os.makedirs("blueprints", exist_ok=True)

        with open(plan_file, "w", encoding="utf-8") as f:
            yaml.dump({"ideas": blueprint_ideas}, f)

        print(f"📁 New blueprint saved to: {plan_file}")
        send_message("scribe", "architect", f"📜 Blueprint created with {len(blueprint_ideas)} items.")
    else:
        print("✅ No new errors found. No blueprint needed.")

if __name__ == "__main__":
    main()
