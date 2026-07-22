from F8_1_Market_Dynamics_Engine import append_observation, emit_market_health
import os

MARKET_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_theory_market_v2.jsonl"
OBSERVATIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_observations.jsonl"
REJECTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_rejections.jsonl"

def reset_env():
    for p in [MARKET_PATH, OBSERVATIONS_PATH, REJECTIONS_PATH]:
        if os.path.exists(p): os.remove(p)
    import F8_Epistemic_Theory_Market_v2 as init
    init.initialize_market()

def run_tests():
    print("--- RUNNING F8.2 ADMISSION GATE TESTS ---\n")
    reset_env()
    
    print("Test 1: Missing Fields")
    append_observation({
        "theory_group_id": "G4",
        "supports_theory_id": "T4"
        # missing weight, reason, is_drill, source
    })
    
    print("\nTest 2: Weight out of bounds (0 < weight <= 5.0)")
    append_observation({
        "theory_group_id": "G4",
        "supports_theory_id": "T4",
        "evidence_weight": 999.0,
        "reason": "Poisoned weight",
        "is_drill": True,
        "source": "test harness"
    })
    
    print("\nTest 3: Taxonomy Mismatch")
    append_observation({
        "theory_group_id": "G1",
        "supports_theory_id": "T4",
        "evidence_weight": 4.0,
        "reason": "Wrong theory for group",
        "is_drill": True,
        "source": "test harness"
    })
    
    print("\nTest 4: Non-drill without provenance")
    append_observation({
        "theory_group_id": "G4",
        "supports_theory_id": "T4",
        "evidence_weight": 4.0,
        "reason": "Real world data",
        "is_drill": False,
        "source": "live log"
        # missing provenance
    })
    
    print("\nTest 5: 'test harness' source on non-drill")
    append_observation({
        "theory_group_id": "G4",
        "supports_theory_id": "T4",
        "evidence_weight": 4.0,
        "reason": "Trying to spoof",
        "is_drill": False,
        "source": "test harness",
        "provenance": "fake"
    })

    print("\nTest 6: Valid Event (Should Pass)")
    append_observation({
        "theory_group_id": "G4",
        "supports_theory_id": "T4",
        "evidence_weight": 5.0,
        "reason": "Valid structural test",
        "is_drill": True,
        "source": "test harness"
    })

    print("\n--- REJECTION LEDGER CONTENTS ---")
    if os.path.exists(REJECTIONS_PATH):
        with open(REJECTIONS_PATH, 'r') as f:
            for line in f:
                print(line.strip())
    else:
        print("No rejections found!")

if __name__ == "__main__":
    run_tests()
