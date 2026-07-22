from datetime import datetime
from ruamel.yaml import YAML
from constructs.construct_comm_relay import send_message, retrieve_messages

VAULT_PATH = "archivist/vault.yaml"
yaml = YAML()

def log_construct_result(name, status, insight=None, next_suggestion=None):
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except FileNotFoundError:
        data = {}

    data.setdefault("construct_feedback", [])

    entry = {
        "timestamp": datetime.now().isoformat(),
        "construct": name,
        "status": status,
        "insight": insight or "None",
        "suggest_next": next_suggestion or "None"
    }

    data["construct_feedback"].append(entry)

    try:
        with open(VAULT_PATH, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
    except Exception as e:
        print(f"⚠️ Feedback log failed: {e}")

def signature():
    return {
        "name": "Sentinel",
        "purpose": "Monitor anomalies and reinforce boundaries",
        "requires": ["vault.yaml", "comm_relay"],
        "last_run": None,
        "status": "active"
    }

def respond():
    return "🛡️ Sentinel standing guard."

def receive(msg):
    print(f"🛎️ Sentinel received alert: {msg}")

def main():
    construct_name = "Sentinel"
    try:
        print(f"👁️ Sentinel scanning...")

        messages = retrieve_messages("sentinel")
        for m in messages:
            sender = m["from"]
            message = m["message"]
            print(f"📬 From {sender}: {message}")

            if "anomaly" in message.lower():
                send_message("architect", "sentinel", "Alert: anomaly detected in message stream.")
                insight = f"Anomaly reported by {sender}."
                suggestion = "Reinforce construct protocol."
            elif "cycle complete" in message.lower():
                send_message("navigator", "sentinel", "All systems holding steady.")
                insight = f"Cycle closure acknowledged from {sender}."
                suggestion = "Standby for next event."
            else:
                send_message("scribe", "sentinel", f"Log entry received from {sender}.")
                insight = f"Message received from {sender}."
                suggestion = "Continue passive monitoring."

            log_construct_result(
                name=construct_name,
                status="message_processed",
                insight=insight,
                next_suggestion=suggestion
            )

        # Final passive entry
        log_construct_result(
            name=construct_name,
            status="success",
            insight="Sentinel completed message scan successfully.",
            next_suggestion="..."
        )

    except Exception as e:
        log_construct_result(name=construct_name, status="error", insight=str(e))

if __name__ == "__main__":
    main()
