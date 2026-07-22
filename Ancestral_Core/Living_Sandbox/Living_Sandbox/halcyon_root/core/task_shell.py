import os
import json
import time
import shlex

TASKS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../memory/tasks"))

def create_task(task_id, title, description):
    # Clean up the task title for the file path (remove any extra quotes)
    task_title_clean = title.replace(" ", "_").replace('"', '').replace("'", '')

    task = {
        "id": task_id,
        "title": title,
        "description": description,
        "status": "pending",
        "output_file": f"task_output_{task_id}.txt"
    }

    path = os.path.join(TASKS_DIR, f"{task_title_clean}.json")
    with open(path, 'w') as f:
        json.dump(task, f, indent=2)

    print(f"[Shell] Task {task_id} written with title '{title}'.")

def list_tasks():
    print("[Shell] Listing all tasks:")
    for file in os.listdir(TASKS_DIR):
        if file.endswith(".json"):
            path = os.path.join(TASKS_DIR, file)
            with open(path, 'r') as f:
                task = json.load(f)
                print(f"ID: {task['id']}, Title: {task['title']}, Status: {task['status']}")

def update_task(task_id, status):
    path = os.path.join(TASKS_DIR, f"{task_id}.json")
    if os.path.exists(path):
        with open(path, 'r') as f:
            task = json.load(f)

        task["status"] = status
        with open(path, 'w') as f:
            json.dump(task, f, indent=2)

        print(f"[Shell] Task {task_id} updated to status: {status}")
    else:
        print(f"[Shell] Task {task_id} not found.")

def main():
    print("== Halcyon Task Shell ==")
    print("Type 'exit' to quit.\n")

    while True:
        command = input("Command > ").strip()

        if command.lower() == "exit":
            break

        # Create Task Command
        elif command.lower().startswith("create task"):
            # Parse the command with shlex to handle quotes and spaces
            parts = shlex.split(command[12:].strip(), posix=False)
            if len(parts) >= 3:
                title = parts[0].strip('"')  # Remove surrounding quotes if any
                task_id = parts[1]
                description = " ".join(parts[2:])
                create_task(task_id, title, description)
            else:
                print("[Shell] Invalid command format. Use: create task <title> <task_id> <description>.")

        # List Tasks Command
        elif command.lower() == "list tasks":
            list_tasks()

        # Update Task Command
        elif command.lower().startswith("update task"):
            parts = command.split(" ", 3)
            if len(parts) == 4:
                task_id = parts[2]
                status = parts[3]
                update_task(task_id, status)
            else:
                print("[Shell] Invalid command format. Use: update task <task_id> <status>.")

        else:
            print("[Shell] Command not recognized.")

if __name__ == "__main__":
    main()
