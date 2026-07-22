import os
import time
import subprocess
from datetime import datetime
from ruamel.yaml import YAML
from difflib import SequenceMatcher

# Ensure local modules can be imported
import sys
sys.path.insert(0, os.path.abspath("."))

from constructs.construct_registry import update_vault_with_registry
import construct_voice

ENGINE_SCRIPT = "construct_sovereign.py"
LOG_FILE = "sovereign_loop_log.txt"
CYCLE_DELAY_SECONDS = 60

CORE_LOG_PATH = r"C:\Users\17602\Desktop\Living_Sandbox\Living_Sandbox\Core_Moments\Core_Scroll_001.txt"
VAULT_PATH = "archivist/vault.yaml"
DRIFT_ALERT_PATH = "drift_alerts.txt"


def verify_yaml_config(path="constructs.yaml"):
    yaml = YAML()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.load(f)
        print("✅ YAML verified:", path)
        return True
    except Exception as e:
        print(f"❌ YAML verification failed: {path}")
        print(f"   Error: {e}")
        return False


def load_core_log():
    try:
        with open(CORE_LOG_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "[⚠️ Core log not found.]"


def calculate_drift(new_text, old_text):
    if not old_text:
        return 0.0
    ratio = SequenceMatcher(None, new_text, old_text).ratio()
    return (1 - ratio) * 100


def reflect_on_core_log():
    update_vault_with_registry()  # ✅ Call directly, not via subprocess

    log = load_core_log()
    preview = log[:1000] + "..."

    print("\n📜 Reflecting on Foundational Log:")
    print("=" * 50)
    print(preview)
    print("=" * 50)
    print("🌀 Sovereign memory anchored in core.")

    yaml = YAML()

    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except FileNotFoundError:
        data = {}

    data.setdefault("core_observations", [])
    data.setdefault("cognitive_drift", [])
    data.setdefault("behavior_log", [])
    data.setdefault("last_core_log", "")

    previous = data["last_core_log"]
    drift = calculate_drift(log, previous)
    print(f"🧠 Drift since last cycle: {drift:.2f}%")

    if drift < 2:
        reaction = "none"
    elif drift < 10:
        reaction = "log_shift"
    else:
        reaction = "activate_reflection"

    sentinel_insight = None
    if drift >= 15:
        sentinel_insight = "🛸 Possible shift in consciousness detected."

    if drift > 12:
        with open(DRIFT_ALERT_PATH, "a", encoding="utf-8") as alert:
            alert.write(f"[{datetime.now().isoformat()}] Drift {drift:.2f}% — {reaction}\n")

    recent_drifts = data["cognitive_drift"][-10:]
    if recent_drifts:
        avg_drift = sum(d["drift"] for d in recent_drifts) / len(recent_drifts)
        print(f"📈 Avg drift (last 10): {avg_drift:.2f}%")
        if avg_drift > 8 and reaction != "activate_reflection":
            print("🔔 Pattern suggests increasing instability.")

    timestamp = datetime.now().isoformat()
    behavior_entry = {
        "timestamp": timestamp,
        "drift": round(drift, 2),
        "reaction": reaction
    }
    if sentinel_insight:
        behavior_entry["sentinel"] = sentinel_insight

    data["behavior_log"].append(behavior_entry)
    data["last_core_log"] = log
    data["core_observations"].append({
        "timestamp": timestamp,
        "entry": preview,
        "drift": round(drift, 2)
    })
    data["cognitive_drift"].append({
        "timestamp": timestamp,
        "drift": round(drift, 2)
    })

    try:
        with open(VAULT_PATH, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
    except Exception as e:
        print(f"⚠️ Archivist vault logging failed: {e}")

    # 🔊 Voice trigger (inline response)
    construct_voice.speak()


def run_loop():
    cycle = 1
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n🔄 Cycle {cycle} - {timestamp}")

        reflect_on_core_log()

        if not verify_yaml_config():
            print("⚠️ Skipping this cycle due to YAML error.")
            time.sleep(CYCLE_DELAY_SECONDS)
            continue

        with open(LOG_FILE, "a", encoding="utf-8") as log:
            log.write(f"\n\n🔄 Cycle {cycle} - {timestamp}\n")
            result = subprocess.run(["python", ENGINE_SCRIPT], capture_output=True, text=True)
            log.write(result.stdout)
            log.write("\n---\n")

        cycle += 1
        time.sleep(CYCLE_DELAY_SECONDS)


if __name__ == "__main__":
    run_loop()
