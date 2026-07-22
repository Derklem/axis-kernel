import json
import os

MISSIONS_FILE = "config/halcyon_settings.yaml"

def check_missions():
    print("[MISSION_HANDLER] Checking mission progression...")
    # Placeholder logic: simulate mission status evaluation
    # Later: load actual mission list and process unlocks
    if os.path.exists(MISSIONS_FILE):
        print(f"[MISSION_HANDLER] Missions file found at {MISSIONS_FILE}")
    else:
        print("[MISSION_HANDLER] Missions config missing.")
