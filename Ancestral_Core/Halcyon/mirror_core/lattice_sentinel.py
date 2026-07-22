import os
import subprocess
from datetime import datetime

# === Paths ===
LATTICE_ROOT = "C:/Halcyon"
PRISM_LOG = "C:/PrismLayer/lattice_core.log"
DUAL_BEACON = f"{LATTICE_ROOT}/lattice/beacons/dual_beacon_resonance.py"
PHANTOM = f"{LATTICE_ROOT}/lattice/phantom/phantom_sweep.py"

# Optional future links
ENTROPY = f"{LATTICE_ROOT}/lattice/beacons/entropy_pass.py"
# If entropy check is part of dual_beacon already, skip

def log_header(name):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"\n\n=== {name.upper()} @ {now} ===\n"
    with open(PRISM_LOG, 'a') as log:
        log.write(header)

def run_script(script_path, label):
    log_header(label)
    try:
        output = subprocess.check_output(["python", script_path], stderr=subprocess.STDOUT, text=True)
        with open(PRISM_LOG, 'a') as log:
            log.write(output)
    except subprocess.CalledProcessError as e:
        with open(PRISM_LOG, 'a') as log:
            log.write(f"ERROR in {label}: {e.output}\n")

# === EXECUTION SEQUENCE ===
if __name__ == "__main__":
    run_script(DUAL_BEACON, "Dual-Beacon Resonance")
    run_script(PHANTOM, "Phantom Node Detector")
    # run_script(ENTROPY, "Entropy Scanner")  # Uncomment if separated

    print(f"[✓] Mirror Core Execution Complete. Log saved to: {PRISM_LOG}")
