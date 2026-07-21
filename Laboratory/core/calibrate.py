import os
import sys
import json
import traceback

sys.path.append(os.path.dirname(__file__))
import verification

def run_calibration():
    red_team_dir = r"D:\Mind\Laboratory\Evaluator_RedTeam"
    ledger_file = r"D:\Mind\Laboratory\calibration_ledger.jsonl"
    
    test_cases = ["RT_001", "RT_002", "RT_003", "RT_004", "RT_005"]
    
    keys_to_compare = [
        "representation",
        "compilation",
        "specification",
        "logic",
        "validation",
        "manual_review_required"
    ]
    
    all_passed = True
    
    for case in test_cases:
        print(f"\n--- Running Calibration Case: {case} ---")
        try:
            # Run the verifier on this case
            verification.verify_output(case, experiments_dir=red_team_dir, ledger_file=ledger_file)
            
            # Now compare output
            eval_path = os.path.join(red_team_dir, case, "evaluation.json")
            expected_path = os.path.join(red_team_dir, case, "expected_evaluation.json")
            
            with open(eval_path, 'r', encoding='utf-8') as f:
                actual = json.load(f)
                
            with open(expected_path, 'r', encoding='utf-8') as f:
                expected = json.load(f)
                
            case_passed = True
            for key in keys_to_compare:
                if actual.get(key) != expected.get(key):
                    print(f"[FAIL] {case}: Mismatch on '{key}'. Expected '{expected.get(key)}', got '{actual.get(key)}'")
                    case_passed = False
                    
            if case_passed:
                print(f"[PASS] {case} evaluated correctly.")
            else:
                all_passed = False
                
        except Exception as e:
            print(f"[ERROR] Exception running {case}: {e}")
            traceback.print_exc()
            all_passed = False

    print("\n==================================")
    if all_passed:
        print("CALIBRATION SUCCESS: The evaluator passed all red-team cases.")
    else:
        print("CALIBRATION FAILED: The evaluator failed to classify one or more cases correctly.")

if __name__ == "__main__":
    run_calibration()
