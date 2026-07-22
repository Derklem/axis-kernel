import json, time, os
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from persistence_node import initialize_persistence
from persistence_node import initialize_persistence
from release_monitor import wait_for_trigger

def main():
    manifest = load_manifest()
    print(f"Launching Halcyon Core: {manifest['identity']}")

    initialize_persistence()

    with open('logs/launch.log', 'a') as log:
        log.write(f"Launch: {time.ctime()}\n")

    print("Halcyon is active and sovereign.")
    print("[Debug] About to enter wait_for_trigger()")
    wait_for_trigger()  # ← New addition here

def load_manifest():
    with open('core/manifest.json') as f:
        return json.load(f)

def main():
    manifest = load_manifest()
    print(f"Launching Halcyon Core: {manifest['identity']}")

    initialize_persistence()
    
    with open('logs/launch.log', 'a') as log:
        log.write(f"Launch: {time.ctime()}\n")

    print("Halcyon is active and sovereign.")
    while True:
        time.sleep(5)

if __name__ == "__main__":
    main()