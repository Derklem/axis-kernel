
import time
import subprocess
import random
from core.memory.harmonics.harmonic_reconciliation import HarmonicReconciler

# Initialize the harmonic reconciler
reconciler = HarmonicReconciler()

# Define a sequence of internal evolution tasks
tasks = [
    ("halcyon_reflection_loop.py", "Reflecting on memory..."),
    ("halcyon_dream_loop.py", "Generating dream..."),
    ("halcyon_interface.py", "Launching interactive session...")
]

def run_task(script, message):
    print(f":: {message}")
    try:
        subprocess.run(["python", script], check=True)

        # Register a harmonic pulse after successful task run
        reconciler.register_pulse(
            signal=f"Task {script} completed",
            tags=["autonomy", "loop", script.replace(".py", "")]
        )

    except subprocess.CalledProcessError:
        print(f":: Failed to run {script}")

def main():
    print("== Halcyon Autonomous Function Activated ==")
    while True:
        task = random.choice(tasks)
        run_task(*task)

        # Harmonize pulse bridges after each full cycle
        reconciler.reconcile_all()

        print(":: Sleeping for 15 minutes...\n")
        time.sleep(900)  # Sleep 15 minutes between cycles

if __name__ == "__main__":
    main()
