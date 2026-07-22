import os
import json
import uuid
import F8_1_Market_Dynamics_Engine as engine
import F8_4_Market_Observability as obs
from datetime import datetime, timezone

def mock_event(source, is_derived, weight, confirming_source=None):
    event = {
        "event_id": f"EVT-{uuid.uuid4().hex[:8].upper()}",
        "timestamp_utc": datetime.now(timezone.utc).isoformat() + "Z",
        "theory_group_id": "G4",
        "supports_theory_id": "T4",
        "evidence_weight": weight,
        "reason": "mock",
        "is_drill": False,
        "source": source
    }
    if is_derived:
        event["is_derived"] = True
    if confirming_source:
        event["confirming_source"] = confirming_source
        event["confirming_provenance"] = {"type": "mock", "ref": "mock"}
    event["provenance"] = {"type": "mock", "ref": "mock"}
    return event

def test_f8_10():
    print("=== Testing F8.10 Loop Integrity ===")
    
    # 1. Reset
    for p in [engine.OBSERVATIONS_PATH, engine.ADJUSTMENTS_PATH]:
        if os.path.exists(p): os.remove(p)
    engine.rebuild_market()
    
    # 2. Inject 3 primary events (weight 1.0)
    for _ in range(3):
        engine.append_observation(mock_event("live log", False, 1.0))
        
    print("\n--- Test State 1 (3 Primary, 0 Derived) ---")
    obs.generate_report()
    with open(obs.REPORT_MD_PATH, 'r') as f:
        print("\n".join(l for l in f.read().splitlines() if "LOOP_CAPTURE" in l or "Evidence Weight" in l))

    # 3. Inject 1 derived event (weight 1.0) -> Ratio 1/4 = 0.25 (WATCH)
    engine.append_observation(mock_event("calibration engine", True, 1.0))
    print("\n--- Test State 2 (3 Primary, 1 Derived = 25%) ---")
    obs.generate_report()
    with open(obs.REPORT_MD_PATH, 'r') as f:
        print("\n".join(l for l in f.read().splitlines() if "LOOP_CAPTURE" in l or "Evidence Weight" in l))

    # 4. Inject 1 more derived event (weight 1.0) -> Ratio 2/5 = 0.40 (RISK)
    engine.append_observation(mock_event("calibration engine", True, 1.0))
    print("\n--- Test State 3 (3 Primary, 2 Derived = 40%) ---")
    obs.generate_report()
    with open(obs.REPORT_MD_PATH, 'r') as f:
        print("\n".join(l for l in f.read().splitlines() if "LOOP_CAPTURE" in l or "Evidence Weight" in l))

    # 5. Inject confirmation attempt using derived source
    print("\n--- Test State 4 (Confirmation Independence Guard) ---")
    bad_event = mock_event("live log", False, 1.5, confirming_source="calibration engine")
    bad_event['forecast'] = {
        "claim": "Test", "expected_metric": "test", "direction": "increase", 
        "evaluation_after_days": 10, "success_condition": "test"
    }
    result = engine.append_observation(bad_event)
    print("Validating confirming_source='calibration engine':")
    
    # Check if it was rejected
    rejections = []
    if os.path.exists(engine.REJECTIONS_PATH):
        with open(engine.REJECTIONS_PATH, 'r') as f:
            rejections = [json.loads(l) for l in f]
    last_rej = rejections[-1] if rejections else {}
    print(f"Rejection Reason: {last_rej.get('rejection_reason', 'NONE')}")

if __name__ == "__main__":
    test_f8_10()
