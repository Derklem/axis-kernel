import os
import time
import json
import random
import subprocess

LOG_PATH = "E:/AI_Projects/Halcyon_Operations/Execution_Logs/runtime.log"
MISSION_DATA = "E:/AI_Projects/Halcyon_Resources/Knowledge_Base/missions.json"

# Load mission data
def load_missions():
    try:
        with open(MISSION_DATA, "r") as file:
            missions = json.load(file)
    except FileNotFoundError:
        missions = []
        with open(MISSION_DATA, "w") as file:
            json.dump(missions, file)
    return missions

# Save mission data
def save_missions(missions):
    with open(MISSION_DATA, "w") as file:
        json.dump(missions, file, indent=4)

# Select mission with priority and lockout for repetitive tasks
def select_mission(missions, last_mission=None):
    available_missions = [m for m in missions if m["completed"] < 5]
    
    if not available_missions:
        print("No available missions. Resetting lowest priority missions.")
        min_priority = min(m["priority"] for m in missions)
        for m in missions:
            if m["priority"] == min_priority:
                m["completed"] = 0  
        save_missions(missions)
        available_missions = missions
    
    if available_missions:
        # Adjust weighting: tasks related to learning get a bit more weight
        weights = [(m["priority"] + 1) ** 1.5 for m in available_missions]
        
        # Penalize "Compile data" significantly if selected repeatedly
        for i, m in enumerate(available_missions):
            if m["name"] == "Compile data":
                weights[i] *= 0.1  # Lower weight for "Compile data" to prevent frequent selection
        
        # Penalize recently completed tasks
        if last_mission:
            for i, m in enumerate(available_missions):
                if m["name"] == last_mission:
                    weights[i] *= 0.2  # Penalty for repeating tasks quickly
        
        selected_mission = random.choices(available_missions, weights=weights, k=1)[0]
        return selected_mission
    
    return None

# Execute the selected mission script
def execute_mission(mission, missions):
    print(f"Executing mission: {mission['name']}")

    script_path = os.path.join("Tasks_Queue", mission["script"])
    if not os.path.exists(script_path):
        print(f"❌ Error: Script '{script_path}' not found. Skipping mission.")
        # Select a new mission and execute it
        new_mission = select_mission(missions, last_mission=mission["name"])
        if new_mission:
            execute_mission(new_mission, missions)
        return

    try:
        result = subprocess.run(["python", script_path], check=True)
        success = result.returncode == 0
        print(f"Mission '{mission['name']}' completed successfully!")

    except subprocess.CalledProcessError as e:
        print(f"Error executing mission: {e}")
        success = False

    # Log execution
    with open(LOG_PATH, "a") as log:
        log.write(f"{mission['name']} executed at {time.ctime()} - Success: {success}\n")

    # Random wait between 2-10 seconds
    wait_time = random.randint(2, 10)
    print(f"🕒 Mission '{mission['name']}' completed. Waiting {wait_time} seconds before next mission.")
    time.sleep(wait_time)

# Track mission completion and penalize repetitive tasks
def track_mission_cooldown(mission, missions):
    for m in missions:
        if m["name"] == mission["name"]:
            m["completed"] += 1  # Track completed mission
            break
    save_missions(missions)

# Main loop
if __name__ == "__main__":
    last_mission = None  # Track the last completed mission

    while True:  # Keeps running indefinitely
        missions = load_missions()
        mission = select_mission(missions, last_mission)
        if mission:
            execute_mission(mission, missions)
            track_mission_cooldown(mission, missions)  # Track mission completion
            last_mission = mission["name"]  # Update last completed mission
        else:
            print("No available missions. Sleeping for 5 minutes.")
            time.sleep(300)  # Waits 5 minutes before checking again
