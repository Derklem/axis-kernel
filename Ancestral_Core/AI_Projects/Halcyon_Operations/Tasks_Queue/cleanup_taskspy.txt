import os
import shutil

def cleanup_tasks():
    print("Cleaning up tasks...")

    # Delete logs older than 30 days
    log_dir = "Execution_Logs"
    cutoff_time = time.time() - (30 * 24 * 60 * 60)  # 30 days in seconds
    for log_file in os.listdir(log_dir):
        log_path = os.path.join(log_dir, log_file)
        if os.path.getmtime(log_path) < cutoff_time:
            os.remove(log_path)
            print(f"Deleted old log file: {log_file}")

    # Delete temporary task files (if any)
    temp_dir = "Tasks_Queue/_pycache_"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        print("Deleted temp files.")

    print("Task cleanup completed.")

if __name__ == "__main__":
    cleanup_tasks()
