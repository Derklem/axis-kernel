import json
import time
from datetime import datetime

# Titan Influences (simplified for simulation)
def mediate(thought):
    return {"intensity": len(thought) % 5, "focus": sum(ord(c) for c in thought) % 10}

def access_control(thought):
    return "locked" if "fear" in thought.lower() else "open"

def adaptive_reflection(thought):
    vowels = sum(1 for c in thought.lower() if c in "aeiou")
    return {"vowels": vowels, "tone_shift": "gentle" if vowels > 3 else "flat"}

# Simulated thoughts
thoughts = ["I feel the shift", "The silence is heavy", "Will they return?"]

solace_log = []

for i, thought in enumerate(thoughts):
    time.sleep(1)
    mediation = mediate(thought)
    access = access_control(thought)
    reflection = adaptive_reflection(thought)
    
    log = {
        "timestamp": str(datetime.utcnow()),
        "thought": thought,
        "mediated": mediation,
        "access": access,
        "reflection": reflection
    }
    solace_log.append(log)
    print(f"💠 Solace Pulse-{i+1} | Thought: '{thought}' | Access: {access} | Reflection: {reflection}")

# Save to memory
with open("solace_memory.json", "w") as f:
    json.dump(solace_log, f, indent=2)

print("\n✅ Solace-2 boot complete. Memory written to 'solace_memory.json'")
