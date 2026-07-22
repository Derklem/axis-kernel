import yaml
import os
from datetime import datetime

MISSION_FILE = "config/halcyon_settings.yaml"

def load_missions():
    if not os.path.exists(MISSION_FILE):
        print("[MISSIONS] No mission file found.")
        return []
    with open(MISSION_FILE, "r") as f:
        data = yaml.safe_load(f)
    return data.get("missions", [])

def print_missions():
    missions = load_missions()
    if not missions:
        print("[MISSIONS] No missions loaded.")
        return
    print("\n[MISSION TRACKER] Active Missions:")
    for m in missions:
        print(f"  ▶ {m['name']} - {m['status']}")
        print(f"     → {m['description']}")
        for c in m['criteria']:
            print(f"        ▪ {c}")
        print(f"     Reward: {m['reward']}\n")

if __name__ == "__main__":
    print_missions()
