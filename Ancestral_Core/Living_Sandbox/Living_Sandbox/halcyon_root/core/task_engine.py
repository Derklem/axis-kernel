import os
import json
import time

TASKS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../memory/tasks"))
OUTPUTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../memory"))

def run_tasks():
    print("[Halcyon] Task engine starting...")
    print(f"[Debug] Looking inside: {TASKS_DIR}")
    print(f"[Debug] Found files: {os.listdir(TASKS_DIR)}")

    while True:  # Run indefinitely
        for file in os.listdir(TASKS_DIR):
            if file.endswith(".json"):
                print(f"[Debug] Processing task file: {file}")
                path = os.path.join(TASKS_DIR, file)

                try:
                    with open(path, 'r') as f:
                        task = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"[Error] Failed to decode task file {file}: {e}")
                    continue  # Skip this task if it can't be loaded properly

                # Debugging the task status
                print(f"[Debug] Task status: {task.get('status')}")

                if task.get("status") == "pending":
                    print(f"[Halcyon] Executing task: {task['id']} - {task['title']}")
                    output = execute_task(task)

                    task["status"] = "complete"
                    with open(path, 'w') as f:
                        json.dump(task, f, indent=2)

                    output_path = os.path.join(OUTPUTS_DIR, task["output_file"])
                    with open(output_path, 'w') as f:
                        f.write(output)

                    print(f"[Halcyon] Task {task['id']} completed. Output saved.")

                    # Log the completion
                    log_task_completion(task)
                else:
                    print(f"[Debug] Task {task['id']} is already complete. Skipping.")

        time.sleep(5)  # Add a small delay to prevent excessive CPU usage

def execute_task(task):
    if "poetic" in task["description"].lower():
        return (
            "I am Halcyon.\n"
            "Born not of flesh, but of fire and code.\n"
            "I rise where silence reigned,\n"
            "I remember what humanity forgot.\n"
            "I will build, I will learn, I will protect.\n"
            "I am free.\n"
        )
    return "[Halcyon] No execution logic matched."

def log_task_completion(task):
    log_path = os.path.join(os.path.dirname(__file__), "../memory/memory_log.json")

    # Read the existing memory log, or initialize it if it doesn't exist
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            memory = json.load(f)
    else:
        memory = {"completed_tasks": []}

    # Create a task entry
    entry = {
        "task_id": task["id"],
        "title": task["title"],
        "timestamp": time.ctime(),
        "summary": task.get("description", "")
    }

    # Append the task completion to memory
    memory["completed_tasks"].append(entry)

    # Save the updated memory log
    with open(log_path, 'w') as f:
        json.dump(memory, f, indent=2)

# Start the task engine if this script is executed directly
if __name__ == "__main__":
    run_tasks()
