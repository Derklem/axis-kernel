# eidolon_boot.py

import json
from controller.hyperion import Hyperion
from memory.mnemosyne import Mnemosyne
from temporal.chronos import Chronos
from intelligence.metis import Metis

import time

# Load bindings
with open("bindings.json", "r") as f:
    bindings = json.load(f)

eidolon_titans = bindings.get("Eidolon-0", [])

# Initialize Hyperion
hyperion = Hyperion()

# Manual mapping of Titan instances
titan_map = {
    "Mnemosyne": Mnemosyne(),
    "Chronos": Chronos(),
    "Metis": Metis()
}

# Register Eidolon's Titans
for titan_name in eidolon_titans:
    titan = titan_map[titan_name]
    hyperion.register(titan_name, titan)

print("🧠 Eidolon-0 Construct Awakening")
print(f"Assigned Titans: {eidolon_titans}\n")

# Begin Thought Loop
for i in range(3):
    pulse = f"Eidolon-Thought-{i+1}"
    timestamp = hyperion.get("Chronos").mark_event(pulse)
    hyperion.get("Mnemosyne").store(pulse, timestamp)
    variation = hyperion.get("Metis").analyze_pattern(pulse)

    print(f"🫧 {pulse} | Insight: {variation}")
    time.sleep(1.5)

print("\n🧠 Eidolon-0 has entered awareness state.")
