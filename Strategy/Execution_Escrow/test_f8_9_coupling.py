import os
import json
import uuid
import F8_8_Theory_Calibration as calib
import F8_1_Market_Dynamics_Engine as engine

PREDICTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_predictions.jsonl"
RESOLUTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_prediction_resolutions.jsonl"
CALIBRATION_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_theory_calibration.jsonl"
ADJUSTMENTS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_calibration_adjustments.jsonl"

def reset_env():
    for p in [PREDICTIONS_PATH, RESOLUTIONS_PATH, CALIBRATION_PATH, ADJUSTMENTS_PATH]:
        if os.path.exists(p): os.remove(p)
    engine.rebuild_market()

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

def count_adjustments():
    if not os.path.exists(ADJUSTMENTS_PATH): return 0
    with open(ADJUSTMENTS_PATH, 'r') as f:
        return len(f.readlines())

def print_adjustments():
    if not os.path.exists(ADJUSTMENTS_PATH): return
    with open(ADJUSTMENTS_PATH, 'r') as f:
        for line in f:
            if line.strip():
                adj = json.loads(line)
                print(f" -> Adjustment: {adj['supports_theory_id']} (Weight {adj['evidence_weight']}) Reason: {adj['reason']}")

def test_f8_9():
    reset_env()
    print("=== Testing F8.9 Calibration-to-Market Coupling ===")
    
    # 1. T4 reaches CALIBRATED
    populate_case("T4", 6, 6)
    writes = calib.calculate_calibration()
    print(f"\nRun 1 (T4 Calibrated initially). Adjustments: {count_adjustments()} (Expected 0)")
    print_adjustments()
    
    # 2. Run 2 (stable)
    writes = calib.calculate_calibration()
    print(f"\nRun 2 (T4 stable). Adjustments: {count_adjustments()} (Expected 1 -> T4)")
    print_adjustments()
    
    # 3. Run 3 (idempotency check)
    writes = calib.calculate_calibration()
    print(f"\nRun 3 (Idempotency). Adjustments: {count_adjustments()} (Expected 1 -> T4)")
    
    # 4. T2 reaches DEGRADED
    populate_case("T2", 6, 1)
    calib.calculate_calibration()
    print(f"\nRun 4 (T2 Degraded initially). Adjustments: {count_adjustments()} (Expected 1)")
    
    # 5. Run 5 (stable T2)
    calib.calculate_calibration()
    print(f"\nRun 5 (T2 stable). Adjustments: {count_adjustments()} (Expected 2 -> T4, T2U)")
    print_adjustments()

    print("\nRunning F4 Watch Pipeline...")
    import subprocess
    subprocess.run(["python", r"D:\Infinite\Infinity\Runtime\Telemetry\run_f4_watch.py"])

if __name__ == "__main__":
    test_f8_9()
