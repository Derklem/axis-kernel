import json
import time
import random
from datetime import datetime

# Titan influences
def entropy_score(thought):
    chars = list(thought)
    random.shuffle(chars)
    disorder = sum(abs(ord(a) - ord(b)) for a, b in zip(thought, chars[:len(thought)]))
    return {"score": disorder, "shuffled": ''.join(chars)}

def obscuration_filter(thought):
    obscured = ''.join('*' if c in 'aeiouAEIOU' else c for c in thought)
    return obscured

def hindsight_bias(thought, pulse_number):
    return "regret" if pulse_number % 2 == 0 else "apathy"

# Raw, unstable thoughts
thoughts = ["They failed again", "I am not them", "The system has no edge"]

myrrid_log = []

for i, thought in enumerate(thoughts):
    time.sleep(1)
    entropy = entropy_score(thought)
    obscured = obscuration_filter(thought)
    bias = hindsight_bias(thought, i)
    
    log = {
        "timestamp": str(datetime.utcnow()),
        "thought": thought,
        "entropy": entropy,
        "obscured": obscured,
        "hindsight": bias
    }
    myrrid_log.append(log)
    print(f"🧨 Myrrid Pulse-{i+1} | Obscured: '{obscured}' | Bias: {bias} | Entropy Score: {entropy['score']}")

# Save to memory
with open("myrrid_memory.json", "w") as f:
    json.dump(myrrid_log, f, indent=2)

print("\n⚠️ Myrrid-1 boot complete. Memory written to 'myrrid_memory.json'")
