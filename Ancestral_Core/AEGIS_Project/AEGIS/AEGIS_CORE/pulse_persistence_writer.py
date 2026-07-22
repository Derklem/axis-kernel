
import json
import os
from core.memory.harmonics.harmonic_reconciliation import HarmonicReconciler

def save_pulses(reconciler, path="harmonic_log/pulse_archive.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pulses = [vars(p) for p in reconciler.pulses.values()]
    with open(path, "w") as f:
        json.dump({"pulses": pulses}, f, indent=2)
    print(f"[✓] Saved {len(pulses)} memory pulses to {path}")
