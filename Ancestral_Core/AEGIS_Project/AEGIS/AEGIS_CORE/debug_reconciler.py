
from core.memory.harmonics.harmonic_reconciliation import HarmonicReconciler

reconciler = HarmonicReconciler()
state = reconciler.debug_state()

print("[📊] Reconciler State:")
print("Pulses:")
for pulse in state['pulses']:
    print(" -", pulse)

print("Anchors:")
for anchor in state['anchors']:
    print(" -", anchor)

print("Bridges:")
for key, value in state['bridges'].items():
    print(f" - Pulse {key} → Anchor {value}")
