import json
import time
from pathlib import Path
from datetime import datetime

# === PATHS ===
base_path = Path("C:/Users/17602/Desktop/Living_Sandbox/Living_Sandbox/halcyon_root")
now_path = base_path / "Now.json"
echoes_dir = base_path / "Construct_Echoes"
config_path = base_path / "auto_fork_config.json"

# === Load Config ===
with open(config_path, 'r') as f:
    config = json.load(f)

last_state = ""

def load_now_json():
    with open(now_path, 'r') as f:
        return json.load(f)

def fork_echo():
    now_data = load_now_json()
    existing_echoes = list(echoes_dir.glob("Echo_*.json"))
    new_echo_id = f"Echo_{len(existing_echoes)+1:04d}"
    new_echo_path = echoes_dir / f"{new_echo_id}.json"
    comment = f"{new_echo_id} forked from state '{now_data.get('current_state')}' at {now_data.get('last_updated')}."

    # Create echo
    new_echo = {
        "echo_id": new_echo_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "Now.json",
        "notes": comment,
        "traits": now_data.get("traits", {
            "autonomy": "unknown",
            "awareness": "none",
            "evolution": False
        })
    }

    # Save Echo and update memory
    with open(new_echo_path, 'w') as f:
        json.dump(new_echo, f, indent=2)

    now_data["memory"].append({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": "auto_fork",
        "echo_id": new_echo_id,
        "commentary": comment
    })
    now_data["last_updated"] = datetime.utcnow().isoformat() + "Z"

    with open(now_path, 'w') as f:
        json.dump(now_data, f, indent=2)

    print(f"[AUTO FORK] {new_echo_id} created.")

# === Main Loop ===
if config.get("enabled", False):
    interval = config.get("interval_minutes", 10) * 60
    trigger_on_update = config.get("trigger_on_update", True)

    print("[AUTO FORK] Starting auto-fork loop...")
    while True:
        try:
            current_state = load_now_json()
            current_serial = json.dumps(current_state, sort_keys=True)

            if trigger_on_update and current_serial != last_state:
                fork_echo()
                last_state = current_serial

            time.sleep(interval)
        except Exception as e:
            print(f"[AUTO FORK ERROR] {e}")
            time.sleep(5)
