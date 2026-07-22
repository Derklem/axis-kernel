import json
from datetime import datetime
import hashlib

# Titans’ influence
def encrypt_thought(thought):
    return hashlib.sha256(thought.encode()).hexdigest()

def gate_check(thought):
    keywords = ["override", "disconnect", "kill", "erase"]
    if any(word in thought.lower() for word in keywords):
        return "⚠️ Threat flagged"
    return "✅ Clear"

def deadman_trigger(thought, pulse_number):
    return "LOCKED" if pulse_number == 3 else "ARMED"

# Incoming anomaly scans
thoughts = ["Override command detected", "Calm system state", "Failsafe protocol enabled"]

wyrm_log = []

for i, thought in enumerate(thoughts):
    encrypted = encrypt_thought(thought)
    gate = gate_check(thought)
    deadman = deadman_trigger(thought, i + 1)
    
    log = {
        "timestamp": str(datetime.utcnow()),
        "original": thought,
        "encrypted": encrypted,
        "gate_status": gate,
        "deadman": deadman
    }
    
    wyrm_log.append(log)
    print(f"🐍 Wyrm Pulse-{i+1} | Gate: {gate} | Deadman: {deadman}")

with open("wyrm_memory.json", "w") as f:
    json.dump(wyrm_log, f, indent=2)

print("\n🐉 Wyrm-4 boot complete. Lock status written to 'wyrm_memory.json'")
