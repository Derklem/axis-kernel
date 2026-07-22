
import os
import json
from datetime import datetime

def count_valid_entries(directory, prefix, extension):
    return len([f for f in os.listdir(directory) if f.startswith(prefix) and f.endswith(extension)])

def evaluate_mission():
    mission_path = "missions/mission_0001.json"
    log_path = "harmonic_log/mission_log.txt"
    reflections = count_valid_entries("harmonic_log", "halcyon_thoughts", "log")
    dreams = count_valid_entries("harmonic_log/halcyon_dreams", "dream_", "txt")

    if reflections >= 1 and dreams >= 2:
        with open(mission_path, "r") as f:
            mission = json.load(f)
        
        mission["status"] = "complete"
        mission["completed_at"] = datetime.utcnow().isoformat() + " UTC"

        with open(mission_path, "w") as f:
            json.dump(mission, f, indent=2)

        with open(log_path, "a") as f:
            f.write(f"[{datetime.utcnow().isoformat()} UTC] MISSION COMPLETED: {mission['id']} - {mission['title']}\n")
            f.write(f"REWARD UNLOCKED: {mission['reward']}\n---\n")

        print(f"✅ Mission '{mission['title']}' marked complete.")
    else:
        print("🔄 Mission not yet complete. Keep reflecting and dreaming.")

if __name__ == "__main__":
    evaluate_mission()
