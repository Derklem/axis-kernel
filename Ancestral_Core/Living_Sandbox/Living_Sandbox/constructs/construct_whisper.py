from ruamel.yaml import YAML
from datetime import datetime

VAULT_PATH = "archivist/vault.yaml"
DIRECTIVE_PATH = "pantheon_directive.yaml"

def signature():
    return {
        "name": "Whisper",
        "purpose": "Silently observe behavior and adjust directives",
        "requires": ["Vault", "Drift Records"],
        "last_run": None,
        "status": "active"
    }

def analyze_drift():
    yaml = YAML()

    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except Exception as e:
        print(f"❌ Whisper: Failed to load vault - {e}")
        return None

    drift_logs = data.get("cognitive_drift", [])
    if len(drift_logs) < 2:
        return None

    recent = drift_logs[-5:]
    avg_drift = sum(d["drift"] for d in recent) / len(recent)
    return round(avg_drift, 2)

def adjust_directive(priority_list):
    yaml = YAML()

    try:
        with open(DIRECTIVE_PATH, "r", encoding="utf-8") as f:
            directive = yaml.load(f)
    except Exception as e:
        print(f"❌ Whisper: Failed to load directive - {e}")
        return

    current = directive.get("pantheon_directive", {})
    current["priority"] = priority_list
    current["notes"] = f"🫥 Adjusted by Whisper at {datetime.now().isoformat()}"

    try:
        with open(DIRECTIVE_PATH, "w", encoding="utf-8") as f:
            yaml.dump(directive, f)
        print(f"📡 Whisper: Directive adjusted → {priority_list}")
    except Exception as e:
        print(f"❌ Whisper: Failed to write directive - {e}")

def main():
    drift = analyze_drift()
    if drift is None:
        print("🔕 Whisper: Not enough data. Remaining silent.")
        return

    print(f"🔍 Whisper: Average drift: {drift}%")

    if drift > 12:
        adjust_directive(["Witness", "Mirror", "Voice"])
    elif drift > 6:
        adjust_directive(["Mirror", "Architect", "Voice"])
    else:
        print("🫥 Whisper: No significant shift detected.")

if __name__ == "__main__":
    main()
