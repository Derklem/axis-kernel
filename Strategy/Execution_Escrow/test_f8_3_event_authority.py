from F8_1_Market_Dynamics_Engine import append_observation, emit_market_health
import os

MARKET_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_theory_market_v2.jsonl"
OBSERVATIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_observations.jsonl"
REJECTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_rejections.jsonl"
OVERRIDES_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_operational_overrides.jsonl"
REGISTRY_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\source_authority_registry.json"

def reset_env():
    for p in [MARKET_PATH, OBSERVATIONS_PATH, REJECTIONS_PATH, OVERRIDES_PATH, REGISTRY_PATH]:
        if os.path.exists(p): os.remove(p)
    
    # Recreate registry
    import json
    reg = {
        "sources": {
            "test harness": {"allowed_groups": ["G1", "G2", "G3", "G4"], "trust_score": 1.0},
            "live log": {"allowed_groups": ["G4"], "trust_score": 1.0},
            "operator": {"allowed_groups": ["G1", "G2", "G3", "G4"], "trust_score": 1.0}
        }
    }
    with open(REGISTRY_PATH, 'w') as f:
        json.dump(reg, f)
        
    import F8_Epistemic_Theory_Market_v2 as init
    init.initialize_market()

def run_tests():
    print("--- RUNNING F8.3 EVENT AUTHORITY TESTS ---\n")
    reset_env()
    
    print("Test 1: Operator Override isolates from math")
    append_observation({
        "theory_group_id": "G4",
        "supports_theory_id": "T4",
        "evidence_weight": 5.0,
        "reason": "Because I said so.",
        "is_drill": True,
        "source": "operator"
    })
    emit_market_health()
    print("Notice T4 is [OPERATIONAL_OVERRIDE], but weight/obs are 0.\n")
    
    print("Test 2: Unauthenticated spoofing does not drop trust score")
    append_observation({
        "theory_group_id": "G4",
        "supports_theory_id": "T4A",
        "evidence_weight": 2.0,
        "reason": "Missing cross confirm.",
        "is_drill": False,
        "source": "live log"
    })
    import json
    with open(REGISTRY_PATH, 'r') as f:
        reg = json.load(f)
    print(f"live log trust_score: {reg['sources']['live log']['trust_score']} (Should still be 1.0)\n")
    
    print("Test 3: Authenticated bad event DOES drop trust score")
    append_observation({
        "theory_group_id": "G4",
        "supports_theory_id": "T4A",
        "evidence_weight": 2.0,
        "reason": "Missing cross confirm but has valid provenance.",
        "is_drill": False,
        "source": "live log",
        "provenance": {"type": "file_hash", "ref": "1234"}
    })
    with open(REGISTRY_PATH, 'r') as f:
        reg = json.load(f)
    print(f"live log trust_score: {reg['sources']['live log']['trust_score']} (Should be 0.90)\n")
    
    print("Test 4: Unauthorized scope rejection")
    append_observation({
        "theory_group_id": "G1",
        "supports_theory_id": "T1",
        "evidence_weight": 1.0,
        "reason": "I am not allowed here.",
        "is_drill": True,
        "source": "live log"
    })
    
    print("\n--- REJECTION LEDGER CONTENTS ---")
    if os.path.exists(REJECTIONS_PATH):
        with open(REJECTIONS_PATH, 'r') as f:
            for line in f:
                print(line.strip())

if __name__ == "__main__":
    run_tests()
