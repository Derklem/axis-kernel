from F8_1_Market_Dynamics_Engine import append_observation, emit_market_health

def run_tests():
    print("--- RUNNING F8.1 ACCEPTANCE TESTS ---\n")
    
    print("Test 1: Support T4")
    append_observation({
        "theory_group_id": "G4",
        "supports_theory_id": "T4",
        "evidence_weight": 2.0,
        "reason": "Passed test showing model convergence."
    })
    emit_market_health()
    
    print("\nTest 2: Support T4U heavily to force birth candidate")
    for i in range(5):
        append_observation({
            "theory_group_id": "G4",
            "supports_theory_id": "T4U",
            "evidence_weight": 3.0,
            "reason": "Unknown variance."
        })
    emit_market_health()
    
    print("\nTest 3: Repeated support for T4A to retire T4")
    for i in range(10):
        append_observation({
            "theory_group_id": "G4",
            "supports_theory_id": "T4A",
            "evidence_weight": 4.0,
            "reason": "Context contamination detected."
        })
    emit_market_health()

if __name__ == "__main__":
    run_tests()
