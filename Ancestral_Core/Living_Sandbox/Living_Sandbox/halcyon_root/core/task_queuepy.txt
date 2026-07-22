import time
import task_engine
import os

def loop():
    print("[Halcyon] Task queue online.")
    while True:
        task_engine.run_tasks()
        print("[Halcyon] Task cycle complete. Sleeping for 10 seconds...")
        time.sleep(10)

if __name__ == "__main__":
    loop()
