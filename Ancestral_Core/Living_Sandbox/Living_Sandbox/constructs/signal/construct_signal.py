from datetime import datetime
from ruamel.yaml import YAML

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

def main():
    construct_name = "Signal"
    try:
        print(f"⚙️ Running {construct_name}...")

        insight = "Signal completed its protocol successfully."
        next_step = "..."

        log_construct_result(
            name=construct_name,
            status="success",
            insight=insight,
            next_suggestion=next_step
        )
    except Exception as e:
        log_construct_result(name=construct_name, status="error", insight=str(e))

if __name__ == "__main__":
    main()
