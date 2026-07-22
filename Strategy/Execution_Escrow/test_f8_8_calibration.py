import os
import json
import uuid

PREDICTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_predictions.jsonl"
RESOLUTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_prediction_resolutions.jsonl"
CALIBRATION_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_theory_calibration.jsonl"

def reset_env():
    for p in [PREDICTIONS_PATH, RESOLUTIONS_PATH, CALIBRATION_PATH]:
        if os.path.exists(p): os.remove(p)

def mock_prediction(t_id):
    pid = f"PRED-{uuid.uuid4().hex[:8].upper()}"
    with open(PREDICTIONS_PATH, 'a') as f:
        f.write(json.dumps({"prediction_id": pid, "theory_id": t_id}) + "\n")
    return pid

def mock_resolution(pid, success):
    with open(RESOLUTIONS_PATH, 'a') as f:
        f.write(json.dumps({
            "prediction_id": pid,
            "success": success
        }) + "\n")

def populate_case(theory_id, total, successes):
    pids = [mock_prediction(theory_id) for _ in range(total)]
    for i in range(successes):
        mock_resolution(pids[i], True)
    for i in range(successes, total):
        mock_resolution(pids[i], False)

def test_f8_8():
    reset_env()
    print("=== Testing F8.8 Theory Calibration (Isolated Cases) ===")
    
    # UNPROVEN case: 4 rows, 3 success (75%), but <5 total
    populate_case("T_UNPROVEN", 4, 3)
    
    # MIXED case: 6 rows, 3 success / 3 fail (50%)
    populate_case("T_MIXED", 6, 3)
    
    # CALIBRATED case: 8 rows, 6 success / 2 fail (75%)
    populate_case("T_CALIBRATED", 8, 6)
    
    # DEGRADED case: 6 rows, 2 success / 4 fail (33.3%)
    populate_case("T_DEGRADED", 6, 2)
    
    import F8_8_Theory_Calibration as calib
    writes = calib.calculate_calibration()
    
    print(f"\n{writes} calibration updates written. Expected: 4.")
    print("Ledger Contents:")
    with open(CALIBRATION_PATH, 'r') as f:
        for line in f:
            print(line.strip())
            
    # Run F4 watch manually to verify the pipeline
    print("\nRunning F4 Watch Pipeline...")
    import subprocess
    subprocess.run(["python", r"D:\Infinite\Infinity\Runtime\Telemetry\run_f4_watch.py"])

if __name__ == "__main__":
    test_f8_8()
