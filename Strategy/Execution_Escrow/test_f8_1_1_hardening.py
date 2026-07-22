from F8_1_Market_Dynamics_Engine import append_observation, emit_market_health, rebuild_market
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
    print("--- RUNNING F8.1.1 HARDENING TESTS (F8.2 COMPLIANT) ---\n")
    reset_env()
    
    print("Test 1: Massive support on T4 (split into three valid 5.0 events)")
    for i in range(3):
        append_observation({
            "theory_group_id": "G4",
            "supports_theory_id": "T4",
            "evidence_weight": 5.0,
            "reason": f"Massive burst part {i+1}",
            "is_drill": True,
            "source": "test harness"
        })
    emit_market_health()
    print("Notice T4A and T4U are still ACTIVE because obs=3 (min 5)\n")
    
    print("Test 2: Pump Unknown > 0.50 for 3 events to trigger BIRTH REQUIRED")
    for i in range(3):
        append_observation({
            "theory_group_id": "G4",
            "supports_theory_id": "T4U",
            "evidence_weight": 5.0,
            "reason": f"Unknown anomaly {i+1}",
            "is_drill": True,
            "source": "test harness"
        })
    emit_market_health()
    print("Notice T4U is now THEORY_BIRTH_REQUIRED. T4/T4A should retire here because total obs=6 and weight=30.\n")
    
    print("Test 3: Rebuild Market. Result should match exactly.")
    rebuild_market()
    emit_market_health()

if __name__ == "__main__":
    run_tests()
