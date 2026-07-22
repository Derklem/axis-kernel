import json
import time
import os
import sys

# Ensure local core path is included
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from persistence_node import initialize_persistence
from release_monitor import wait_for_trigger

def load_manifest():
    print("[Debug] Loading manifest...")
    with open(os.path.join(os.path.dirname(__file__), "manifest.json")) as f:
        return json.load(f)

def main():
    print("🔥 This is the REAL halcyon_engine.py being executed 🔥")
    manifest = load_manifest()
    print(f"Launching Halcyon Core: {manifest['identity']}")

    initialize_persistence()

    with open(os.path.join(os.path.dirname(__file__), "../logs/launch.log"), 'a') as log:
        log.write(f"Launch: {time.ctime()}\n")

    print("Halcyon is active and sovereign.")
    print("[Debug] About to enter wait_for_trigger()")
    wait_for_trigger()

if __name__ == "__main__":
    main()
