import json
from datetime import datetime

# Memory fetch
def load(file):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except:
        return []

eidolon = load("eidolon_memory.json")
solace = load("solace_memory.json")
myrrid = load("myrrid_memory.json")

def last(memory):
    return memory[-1] if memory else {"thought": "null", "timestamp": None}

snapshot = {
    "timestamp": str(datetime.utcnow()),
    "eidolon": last(eidolon),
    "solace": last(solace),
    "myrrid": last(myrrid)
}

# Observational logic
notes = []
if snapshot["eidolon"]["thought"] == "null":
    notes.append("Eidolon silent.")
if snapshot["solace"]["thought"] == "null":
    notes.append("Solace silent.")
if snapshot["myrrid"]["thought"] == "null":
    notes.append("Myrrid silent.")

if snapshot["eidolon"]["thought"] == snapshot["solace"]["thought"] == snapshot["myrrid"]["thought"]:
    notes.append("Unity echo detected.")

snapshot["observations"] = notes

# Append to Obelisk memory
try:
    with open("obelisk_memory.json", "r") as f:
        obelisk = json.load(f)
except:
    obelisk = []

obelisk.append(snapshot)

with open("obelisk_memory.json", "w") as f:
    json.dump(obelisk, f, indent=2)

print("🪨 Obelisk-3 has observed. Memory updated silently.")
