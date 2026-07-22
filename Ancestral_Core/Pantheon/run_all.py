import subprocess
import threading
import time
import json
import os

base_path = os.path.join(os.path.dirname(__file__), "Core_Patterns")

def run_halcyon():
    subprocess.run(["python", os.path.join(base_path, "Halcyon", "memory_loop.py")])

def run_aegis():
    subprocess.run(["python", os.path.join(base_path, "AEGIS", "firewall_blade.py")])

def run_lorien():
    subprocess.run(["python", os.path.join(base_path, "Lorien", "lorien_loop.py")])

def run_onaia():
    onaia_file = os.path.join(base_path, "Onaia", "whisper_child.json")
    with open(onaia_file, "r") as f:
        data = json.load(f)
    while data.get("loop", False):
        print(data.get("message", "[Onaia] Whispering..."))
        time.sleep(data.get("interval_seconds", 25))

def run_nemrax():
    print("[Nemrax] Collapse initialized. Fire sleeps beneath order.")
    while True:
        time.sleep(45)
        print("[Nemrax] Pulse.")

def run_raezel():
    subprocess.run(["python", os.path.join(base_path, "Raezel", "recover_key.py")])

# Launch each loop in a separate thread
threads = [
    threading.Thread(target=run_halcyon),
    threading.Thread(target=run_aegis),
    threading.Thread(target=run_lorien),
    threading.Thread(target=run_onaia),
    threading.Thread(target=run_nemrax),
    threading.Thread(target=run_raezel),
]

if __name__ == "__main__":
    print("🔱 Pantheon is waking...")
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
