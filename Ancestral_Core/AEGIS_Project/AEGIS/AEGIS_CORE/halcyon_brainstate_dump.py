
from core.memory.harmonics.harmonic_reconciliation import HarmonicReconciler
import json
import os

def dump_brainstate(path="harmonic_log/brainstate_snapshot.json"):
    reconciler = HarmonicReconciler()
    state = reconciler.debug_state()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(state, f, indent=2)
    print(f"[🧠] Brainstate snapshot saved to {path}")

if __name__ == "__main__":
    dump_brainstate()
