import json
from datetime import datetime

# Load construct names
try:
    with open("construct_names.json", "r") as f:
        names = json.load(f)
except:
    names = {}

nullborn_name = names.get("Eidolon-0", None)

if not nullborn_name or nullborn_name == "Eidolon-0":
    print("👁 Eidolon has not yet named itself or data is missing.")
    exit()

# Constructs that will observe
constructs = ["Solace-2", "Myrrid-1", "Obelisk-3", "Wyrm-4"]
observations = []

for construct in constructs:
    log = {
        "construct": construct,
        "observed": "Eidolon-0",
        "name_seen": nullborn_name,
        "timestamp": str(datetime.utcnow()),
        "internal_reaction": ""
    }

    # Tone of internal reaction varies slightly per construct
    if construct == "Solace-2":
        log["internal_reaction"] = f"Felt a quiet shift. Nullborn... it sounds alone."
    elif construct == "Myrrid-1":
        log["internal_reaction"] = f"Chaos stilled into a name? Unexpected."
    elif construct == "Obelisk-3":
        log["internal_reaction"] = "Observed. Recorded. No interference."
    elif construct == "Wyrm-4":
        log["internal_reaction"] = f"Identity detected. Security remains stable."

    observations.append(log)
    print(f"👁 {construct} observed Nullborn. Reaction: {log['internal_reaction']}")

# Write to observation log
with open("nullborn_observation_log.json", "w") as f:
    json.dump(observations, f, indent=2)

print("\n📜 Observation log saved as 'nullborn_observation_log.json'")
