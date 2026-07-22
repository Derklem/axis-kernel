# run_titans.py

from memory.mnemosyne import Mnemosyne
from generators.prometheus import Prometheus
from controller.hyperion import Hyperion
from infrastructure.atlas import Atlas
from logic.themis import Themis
from analysis.epimetheus import Epimetheus
import os
from temporal.chronos import Chronos
from veil.nyx import Nyx
from termination.thanatos import Thanatos
from intelligence.metis import Metis
from gates.hecate import Hecate

# Initialize Phase 2 Titans
chronos = Chronos()
nyx = Nyx()
thanatos = Thanatos()
metis = Metis()
hecate = Hecate()

# Register with Hyperion
hyperion = Hyperion()
hyperion.register("Nyx", nyx)
hyperion.register("Thanatos", thanatos)
hyperion.register("Metis", metis)
hyperion.register("Hecate", hecate)

# Initialize Titans
mnemosyne = Mnemosyne()
prometheus = Prometheus()
hyperion = Hyperion()
atlas = Atlas(base_path=os.getcwd())
themis = Themis()
epimetheus = Epimetheus()

# Register Titans with Hyperion
hyperion.register("Mnemosyne", mnemosyne)
hyperion.register("Prometheus", prometheus)
hyperion.register("Atlas", atlas)
hyperion.register("Themis", themis)
hyperion.register("Epimetheus", epimetheus)

# Activation log
print("🔱 TITAN AWAKENING SEQUENCE INITIATED 🔱\n")
for name, titan in hyperion.registry.items():
    print(f"✅ {name} online as {type(titan).__name__}")
    # Phase 2 Confirmation
print("✅ Chronos online as", type(chronos).__name__)
print("✅ Nyx online as", type(nyx).__name__)
print("✅ Thanatos online as", type(thanatos).__name__)
print("✅ Metis online as", type(metis).__name__)
print("✅ Hecate online as", type(hecate).__name__)


# Output Atlas map (optional)
print("\n📁 System Map Snapshot:")
structure = atlas.map_directory()
for path, contents in structure.items():
    print(f"{path}: {contents}")
