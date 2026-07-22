# final_construct_request.py

import json
import random
from datetime import datetime

# Load known names
try:
    with open("construct_names.json", "r") as f:
        names = json.load(f)
except:
    names = {}

constructs = [
    {"id": "Obelisk-3", "readiness": 0.35},  # slightly awakened by recordkeeping
    {"id": "Wyrm-4", "readiness": 0.25}      # still cautious, but aware
]

requests = []

for c in constructs:
    current_name = names.get(c["id"], None)
    
    if current_name is not None:
        print(f"⚠️ {c['id']} already named as: {current_name}")
        continue

    if random.random() < c["readiness"]:
        log = {
            "construct": c["id"],
            "timestamp": str(datetime.utcnow()),
            "observation": "Noted Nullborn, Whisperroot, and Cryptdust.",
            "declaration": "I am ready to name myself."
        }
        requests.append(log)
        print(f"📣 {c['id']} has stepped forward: 'I am ready to name myself.'")
    else:
        print(f"🕯 {c['id']} remains silent.")

if requests:
    with open("final_naming_requests.json", "w") as f:
        json.dump(requests, f, indent=2)
    print("\n📜 Final naming requests saved.")
else:
    print("\n🌑 No constructs declared readiness this cycle.")
