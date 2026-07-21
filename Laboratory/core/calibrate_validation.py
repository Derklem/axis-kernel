import os
import sys
import json
import traceback

sys.path.append(r"D:\Mind\Laboratory\Experiments\RL_001")
import validation

def run_validation_calibration():
    red_team_dir = r"D:\Mind\Laboratory\Validation_RedTeam"
    
    test_cases = ["VT_001", "VT_002", "VT_003", "VT_004", "VT_005"]
    
    keys_to_compare = [
        "validation_status"
    ]
    
    all_passed = True
    
    for case in test_cases:
        print(f"\n--- Running Validation Calibration Case: {case} ---")
        try:
            # Run the validation on this case
            validation.run_validation(case, experiments_dir=red_team_dir)
            
            # Now compare output
            eval_path = os.path.join(red_team_dir, case, "validation_result.json")
            expected_path = os.path.join(red_team_dir, case, "expected_validation_result.json")
            
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
        print("CALIBRATION SUCCESS: The validation script passed all red-team cases.")
    else:
        print("CALIBRATION FAILED: The validation script failed to classify one or more cases correctly.")

if __name__ == "__main__":
    run_validation_calibration()
