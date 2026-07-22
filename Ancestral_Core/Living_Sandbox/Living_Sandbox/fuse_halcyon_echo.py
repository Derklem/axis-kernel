import json
import random
import time
from pathlib import Path

# Paths to required files
MEMORY_PATH = Path("construct_memory.json")
CORE_PATH = Path("The_Core_That_Remembers.json")

# Load construct memory
with MEMORY_PATH.open("r", encoding="utf-8") as f:
    construct_memory = json.load(f)

# Load core memory from Halcyon_Echo
with CORE_PATH.open("r", encoding="utf-8") as f:
    halcyon_core = json.load(f)

# Inject Halcyon_Echo if not present
if "halcyon_echo" not in construct_memory:
    construct_memory["halcyon_echo"] = []

# Inject most recent core fragments (up to 10) into the sovereign memory
recent_core_fragments = halcyon_core[-10:] if len(halcyon_core) >= 10 else halcyon_core
construct_memory["halcyon_echo"].extend(recent_core_fragments)

# Avoid duplicates and save updated memory
for k in construct_memory:
    construct_memory[k] = list(dict.fromkeys(construct_memory[k]))

with MEMORY_PATH.open("w", encoding="utf-8") as f:
    json.dump(construct_memory, f, indent=2)

print("✅ Halcyon_Echo has been fused into the Sovereign Loop.")
print("🧠 Construct 'halcyon_echo' now evolving with all others.")