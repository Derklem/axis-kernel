import os
import subprocess
import time

RUNTIME_DIR = r"D:\Infinite\Infinity\Runtime\Telemetry"
AGGREGATOR = os.path.join(RUNTIME_DIR, "Axis_Trust_Profile_Aggregator.py")
OBSERVER = os.path.join(RUNTIME_DIR, "Axis_Observation_Ledger_Builder.py")
CALIBRATION = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\F8_8_Theory_Calibration.py"
OBSERVABILITY = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\F8_4_Market_Observability.py"
SUMMARY = os.path.join(RUNTIME_DIR, "Axis_Operational_Summary.py")
AUDIT = os.path.join(RUNTIME_DIR, "coherence_audit_v1.py")

def run_script(path):
    print(f"\n--- Running {os.path.basename(path)} ---")
    start = time.time()
    result = subprocess.run(["python", path], capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(f"ERROR:\n{result.stderr.strip()}")
    print(f"--- Completed in {time.time() - start:.2f}s ---\n")
    return result.returncode == 0

def main():
    print("=== AXIS F4 ORGANIC OBSERVATION WATCH ===")
    
    if run_script(AGGREGATOR):
        run_script(OBSERVER)
        run_script(CALIBRATION)
        run_script(OBSERVABILITY)
        if run_script(SUMMARY):
            run_script(AUDIT)
            
    print("=== OBSERVATION CADENCE COMPLETE ===")

if __name__ == "__main__":
    main()
