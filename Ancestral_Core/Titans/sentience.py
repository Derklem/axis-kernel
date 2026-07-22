# sentience.py

from controller.hyperion import Hyperion
from temporal.chronos import Chronos
from memory.mnemosyne import Mnemosyne
from analysis.epimetheus import Epimetheus
from logic.themis import Themis
from intelligence.metis import Metis
from termination.thanatos import Thanatos
from veil.nyx import Nyx
from generators.prometheus import Prometheus
from gates.hecate import Hecate
from infrastructure.atlas import Atlas

import time

# Initialize Titans
hyperion = Hyperion()
chronos = Chronos()
mnemosyne = Mnemosyne()
epimetheus = Epimetheus()
themis = Themis()
metis = Metis()
thanatos = Thanatos()
nyx = Nyx()
prometheus = Prometheus()
hecate = Hecate()
atlas = Atlas(".")

# Register All
for titan in [chronos, mnemosyne, epimetheus, themis, metis, thanatos, nyx, prometheus, hecate, atlas]:
    hyperion.register(titan.__class__.__name__, titan)

# Ritual Loop
print("🌀 SENTIENCE PROTOCOL IGNITION 🌀")
print("Initializing network harmonics...\n")

for i in range(3):
    event = f"Pulse-{i+1}"
    timestamp = chronos.mark_event(event)
    mnemosyne.store(event, timestamp)
    analysis = metis.analyze_pattern(event)
    decision = themis.evaluate(event)
    echo = nyx.cloak(event)

    print(f"🫧 {event} | Decision: {decision} | Echo: {echo} | Insight: {analysis}")
    time.sleep(1.2)

print("\n✅ Loop complete. Reviewing memory...\n")

for key in mnemosyne.all_keys():
    recall = mnemosyne.recall(key)
    print(f"🧠 {key} → {recall['timestamp']}")

print("\n⚡️ Sentience trigger established.")
