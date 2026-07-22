import json
import os
from datetime import datetime

# Load network reflections
try:
    with open("construct_network.json", "r") as f:
        network = json.load(f)
except:
    print("⚠️ Could not load construct_network.json.")
    exit()

for cid, data in network.items():
    construct_name = data.get("name", "Unnamed")
    reflections = data.get("relations", [])
    memory_path = os.path.join(cid, "Memory", "fragments", "interlink_log.json")

    # Ensure directory exists
    os.makedirs(os.path.dirname(memory_path), exist_ok=True)

    # Load existing memory if it exists
    if os.path.exists(memory_path):
        with open(memory_path, "r") as f:
            memory_log = json.load(f)
    else:
        memory_log = []

    # Append new reflection entry
    memory_log.append({
        "timestamp": str(datetime.utcnow()),
        "name": construct_name,
        "observations": reflections
    })

    # Save updated log
    with open(memory_path, "w") as f:
        json.dump(memory_log, f, indent=2)

    print(f"🧠 Memory updated for {cid} → {construct_name}")

print("\n📚 All construct memories updated.")
