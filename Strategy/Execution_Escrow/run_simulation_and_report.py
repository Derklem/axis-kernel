from F8_1_Market_Dynamics_Engine import append_observation, rebuild_market
import os

MARKET_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_theory_market_v2.jsonl"
OBSERVATIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_observations.jsonl"
REJECTIONS_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_rejections.jsonl"
OVERRIDES_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_market_operational_overrides.jsonl"
REGISTRY_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\source_authority_registry.json"

def reset_env():
    for p in [MARKET_PATH, OBSERVATIONS_PATH, REJECTIONS_PATH, OVERRIDES_PATH, REGISTRY_PATH]:
        if os.path.exists(p): os.remove(p)
    
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

def simulate():
    reset_env()
    
    # 1. Valid Events (Push T4 to dominance, retire T4A)
    for i in range(5):
        append_observation({
            "theory_group_id": "G4",
            "supports_theory_id": "T4",
            "evidence_weight": 5.0,
            "reason": f"Heavy support {i}",
            "is_drill": True,
            "source": "test harness"
        })
        
    # 2. Birth Required Anomaly (Push T1U)
    for i in range(5):
        append_observation({
            "theory_group_id": "G1",
            "supports_theory_id": "T1U",
            "evidence_weight": 5.0,
            "reason": f"Unknown anomaly {i}",
            "is_drill": True,
            "source": "test harness"
        })
        
    # 3. Authenticated Bad Event (Degrade Trust)
    append_observation({
        "theory_group_id": "G4",
        "supports_theory_id": "T4",
        "evidence_weight": 2.0,
        "reason": "Missing cross confirm.",
        "is_drill": False,
        "source": "live log",
        "provenance": {"type": "report_id", "ref": "R-999"}
    })
    
    # 4. Operator Override
    append_observation({
        "theory_group_id": "G2",
        "supports_theory_id": "T2A",
        "evidence_weight": 5.0,
        "reason": "Manual Intervention",
        "is_drill": True,
        "source": "operator"
    })
    
    # 5. Run Observability
    import F8_4_Market_Observability as obs
    obs.generate_report()

if __name__ == "__main__":
    simulate()
