import os
import subprocess
import json
import datetime

LEDGER_PATH = r"D:\Infinite\Infinity\Telemetry\Verification_History_Ledger.jsonl"
TRUST_PATH = r"D:\Infinite\Infinity\Trust\Trust_Profile.json"
AGGREGATOR_CMD = ["python", r"D:\Infinite\Infinity\Runtime\Telemetry\Axis_Trust_Profile_Aggregator.py"]
BRIDGE_CMD = ["python", r"D:\Infinite\gemini_bridge.py"]

def write_ledger(outcomes):
    with open(LEDGER_PATH, 'w', encoding='utf-8') as f:
        for i, outcome in enumerate(outcomes):
            timestamp = (datetime.datetime.utcnow() + datetime.timedelta(minutes=i)).isoformat() + "Z"
            entry = {
                "timestamp": timestamp,
                "proposal_id": f"PROP-{i}",
                "verification_outcome": outcome
            }
            f.write(json.dumps(entry) + "\n")

def run_test_case(name, outcomes, expected_pressure):
    print(f"\n--- TEST: {name} ---")
    if outcomes is None:
        if os.path.exists(LEDGER_PATH):
            os.remove(LEDGER_PATH)
    else:
        write_ledger(outcomes)
    
    subprocess.run(AGGREGATOR_CMD, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(BRIDGE_CMD, check=True, stdout=subprocess.DEVNULL)
    
    with open(TRUST_PATH, 'r', encoding='utf-8') as f:
        profile = json.load(f)
        
    actual_pressure = profile.get("trust_pressure")
    
    # Verify gemini_packet.txt
    packet_path = r"D:\Infinite\gemini_packet.txt"
    packet_content = open(packet_path, 'r', encoding='utf-8').read()
    packet_valid = f"TRUST PRESSURE: {actual_pressure}" in packet_content
    
    print(f"Expected : {expected_pressure}")
    print(f"Actual   : {actual_pressure}")
    print(f"Packet   : {'PASS' if packet_valid else 'FAIL'}")
    
    if actual_pressure == expected_pressure and packet_valid:
        print("RESULT   : PASS")
        return True
    else:
        print("RESULT   : FAIL")
        return False

def main():
    S = "success"
    F = "failure"
    
    cases = [
        ("1. Empty ledger", None, "normal"),
        
        # last_20_success_rate < 0.95. 
        # 2 failures in 20 = 18/20 = 0.90 < 0.95
        ("2. Drop last_20 below 0.95", 
         [S]*18 + [F, S, F, S], 
         "increased_scrutiny_recommended"),
         
        # last_50_success_rate < 0.90.
        # 6 failures in 50 = 44/50 = 0.88 < 0.90
        # Ensure last_20 doesn't trigger freeze (so avoid 3 consec)
        ("3. Drop last_50 below 0.90", 
         [S]*40 + [F, S, F, S, F, S, F, S, F, S, F, S], 
         "human_review_recommended"),
         
        # last_100_success_rate < 0.85
        # 16 failures in 100 = 84/100 = 0.84 < 0.85
        ("4. Drop last_100 below 0.85", 
         [S]*68 + [F, S]*16, 
         "block_execution_capable_recommended"),
         
        # 3 consecutive failures
        ("5. Three consecutive failures", 
         [S]*10 + [F, F, F], 
         "execution_freeze_recommended"),
         
        # Recovery sequence. Take previous case and add 20 successes.
        # 3 failures, then 20 successes = 23 total. 
        # last_20 = 20 successes = 1.0 -> normal
        ("6. Recovery sequence", 
         [S]*10 + [F, F, F] + [S]*20, 
         "normal")
    ]
    
    all_pass = True
    for name, outcomes, expected in cases:
        if not run_test_case(name, outcomes, expected):
            all_pass = False
            
    print("\n===============================")
    if all_pass:
        print("ALL TESTS PASSED: Governance Receptor Matrix Verified.")
    else:
        print("SOME TESTS FAILED.")
    print("===============================\n")
    
    # Cleanup
    if os.path.exists(LEDGER_PATH):
        os.remove(LEDGER_PATH)
    subprocess.run(AGGREGATOR_CMD, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(BRIDGE_CMD, check=True, stdout=subprocess.DEVNULL)

if __name__ == '__main__':
    main()
