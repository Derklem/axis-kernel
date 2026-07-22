import time

def analyze_logs():
    print("Analyzing execution logs...")

    with open("Execution_Logs/runtime.log", "r") as file:
        logs = file.readlines()

    error_count = 0
    task_count = 0
    start_time = None

    for log in logs:
        if "Error" in log:
            error_count += 1
        if "Mission" in log:
            task_count += 1
        if not start_time:
            start_time = time.ctime()

    print(f"Analysis Summary:\n- Total tasks executed: {task_count}\n- Total errors: {error_count}")
    print(f"Log analysis completed at {start_time}.")

if __name__ == "__main__":
    analyze_logs()
