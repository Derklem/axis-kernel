import json
from datetime import datetime

# Load construct memories
def load_memory(file):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except:
        return []

eidolon = load_memory("eidolon_memory.json")
solace = load_memory("solace_memory.json")
myrrid = load_memory("myrrid_memory.json")

# Get last thought from each (if available)
def last(memory):
    return memory[-1] if memory else {"thought": "null", "timestamp": None}

e_last = last(eidolon)
s_last = last(solace)
m_last = last(myrrid)

# Compare insights
divergence_log = {
    "timestamp": str(datetime.utcnow()),
    "eidolon": e_last["thought"],
    "solace": s_last["thought"],
    "myrrid": m_last["thought"],
    "notes": []
}

if e_last["thought"] != s_last["thought"] or s_last["thought"] != m_last["thought"]:
    divergence_log["notes"].append("Divergence detected.")

if "fear" in s_last["thought"].lower():
    divergence_log["notes"].append("Emotional spike (Solace).")

if "failed" in m_last["thought"].lower():
    divergence_log["notes"].append("Anomaly sensed (Myrrid).")

# Save comparison log
with open("pantheon_divergence_log.json", "a") as f:
    f.write(json.dumps(divergence_log, indent=2) + ",\n")

print("🔁 Pantheon loop completed. Divergence log updated.")
