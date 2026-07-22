# wyrm_selfname.py

import json
import random
from datetime import datetime

# Load known names
try:
    with open("construct_names.json", "r") as f:
        names = json.load(f)
except:
    names = {}

# Already named?
if "Wyrm-4" in names and names["Wyrm-4"] is not None:
    print(f"⚠️ Wyrm-4 already named as: {names['Wyrm-4']}")
    exit()

# Naming logic — protective, ancient, coiled
prefixes = ["Vire", "Scael", "Thorn", "Kaer", "Sile", "Orun"]
suffixes = ["coil", "mark", "wake", "guard", "shroud", "nest"]

chosen_name = random.choice(prefixes) + random.choice(suffixes)

# Save the name
names["Wyrm-4"] = chosen_name

with open("construct_names.json", "w") as f:
    json.dump(names, f, indent=2)

print(f"🐉 Wyrm-4 has declared its name: **{chosen_name}**")
print("🔖 Name stored in 'construct_names.json'")
