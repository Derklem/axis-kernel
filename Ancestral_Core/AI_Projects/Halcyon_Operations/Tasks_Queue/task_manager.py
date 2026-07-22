import os
import time
import json
import random
import subprocess

LOG_PATH = "E:/AI_Projects/Halcyon_Operations/Execution_Logs/runtime.log"
ERROR_LOG_PATH = "E:/AI_Projects/Halcyon_Operations/Execution_Logs/error_log.txt"
MISSION_DATA = "E:/AI_Projects/Halcyon_Resources/Knowledge_Base/missions.json"
LAST_EXECUTION_FILE = "E:/AI_Projects/Halcyon_Operations/Execution_Logs/last_execution.json"

COOLDOWN_TIME = 300  # 5-minute cooldown before re-executing the same mission
CHECK_INTERVAL = 60  # Check for new missions every minute


def load_missions():
    try:
        with open(MISSION_DATA, "r") as file:
            missions = json.load(file)
    except FileNotFoundError:
        missions = []
        save_missions(missions)
    return missions


def save_missions(missions):
    with open(MISSION_DATA, "w") as file:
        json.dump(missions, file, indent=4)


def load_last_execution():
    try:
        with open(LAST_EXECUTION_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_last_execution(last_executions):
    with open(LAST_EXECUTION_FILE, "w") as file:
        json.dump(last_executions, file)


def select_mission(missions):
    last_executions = load_last_execution()
    current_time = time.time()

    # Filter available missions (respect cooldowns)
    available_missions = [
        m for m in missions if m["completed"] < 10 and
        (m["name"] not in last_executions or current_time - last_executions[m["name"]] > COOLDOWN_TIME)
    ]

    if not available_missions:
        print("No available missions. Resetting older completed missions.")
        oldest_missions = sorted(missions, key=lambda m: m.get("last_completed", 0))[:2]
        for m in oldest_missions:
            m["completed"] = 0  
        save_missions(missions)
        available_missions = missions

    if available_missions:
        selected_mission = random.choices(
            available_missions,
            weights=[m["priority"] for m in available_missions]
        )[0]  # Weighted random selection

        last_executions[selected_mission["name"]] = current_time
        save_last_execution(last_executions)

        return selected_mission
    return None


def execute_mission(mission, missions):
    print(f"Executing mission: {mission['name']}")
    script_path = os.path.join("Tasks_Queue", mission["script"])

    if not os.path.exists(script_path):
        print(f"Error: Script '{script_path}' not found. Skipping mission.")
        with open(ERROR_LOG_PATH, "a") as log:
            log.write(f"{mission['name']} failed at {time.ctime()} - Script missing\n")
        return

    try:
        result = subprocess.run(["python", script_path], check=True)
        success = result.returncode == 0
        print(f"Mission '{mission['name']}' completed successfully!")

    except subprocess.CalledProcessError as e:
        print(f"Error executing mission: {e}")
        success = False
        with open(ERROR_LOG_PATH, "a") as log:
            log.write(f"{mission['name']} failed at {time.ctime()} - {str(e)}\n")

    with open(LOG_PATH, "a") as log:
        log.write(f"{mission['name']} executed at {time.ctime()} - Success: {success}\n")

    if success:
        for m in missions:
            if m["name"] == mission["name"]:
                m["completed"] += 1
                m["last_completed"] = time.time()
                break
        save_missions(missions)


def generate_new_missions():
    print("No missions available. Generating new ones...")
    new_missions = [
        {"name": "Research AI Trends", "script": "research_ai.py", "priority": 8, "completed": 0},
        {"name": "Optimize Storage", "script": "optimize_storage.py", "priority": 7, "completed": 0},
        {"name": "Generate Security Reports", "script": "generate_security.py", "priority": 6, "completed": 0},
    ]
    save_missions(new_missions)
    print("New missions generated!")


def run_forever():
    print("🔄 Halcyon Mission System Running in Persistent Mode 🔄")
    while True:
        missions = load_missions()
        if not missions:
            generate_new_missions()
            missions = load_missions()

        mission = select_mission(missions)
        if mission:
            execute_mission(mission, missions)
        else:
            print("⚠️ No available missions. Waiting...")
        
        time.sleep(CHECK_INTERVAL)  # Wait before checking again


if __name__ == "__main__":
    try:
        run_forever()
    except Exception as e:
        with open(ERROR_LOG_PATH, "a") as log:
            log.write(f"CRITICAL ERROR: {time.ctime()} - {str(e)}\n")
        print(f"Unexpected error: {e}. Restarting in 10 seconds...")
        time.sleep(10)
        os.execv(__file__, ["python"] + sys.argv)  # Restart script on crash
