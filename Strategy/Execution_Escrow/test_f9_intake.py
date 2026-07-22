import os
import json
import uuid
import F9_External_Intake_Gateway as f9
import F8_1_Market_Dynamics_Engine as engine

def clean_ledgers():
    for p in [f9.INTAKE_PATH, f9.QUARANTINE_PATH, f9.CRITIQUES_PATH, f9.REJECTIONS_PATH, engine.OBSERVATIONS_PATH, engine.REJECTIONS_PATH]:
        if os.path.exists(p):
            os.remove(p)

def read_jsonl(path):
    if not os.path.exists(path): return []
    with open(path, 'r') as f:
        return [json.loads(line) for line in f if line.strip()]

def test_f9():
    print("=== Testing F9.0 External Reality Intake ===")
    clean_ledgers()
    engine.rebuild_market()

    # 1. Test Lane B (Raw Narrative)
    print("\n[Test 1] Injecting Lane B (Raw Narrative Critique)...")
    payload_b = {
        "source_entity": "Model_X",
        "raw_payload": "The system assumes T4 is true, but external evidence suggests T4A is more likely."
    }
    r = f9.process_intake(payload_b)
    print(f"Result: {r['status']}")
    
    critiques = read_jsonl(f9.CRITIQUES_PATH)
    print(f"Critiques Ledger Count: {len(critiques)}")

    # 2. Test Lane A (Inadmissible Type)
    print("\n[Test 2] Injecting Lane A (Speculation)...")
    payload_a_inadmissible = {
        "source_entity": "Operator_Dave",
        "claims": [{
            "claim_text": "I think T2 is going to fail soon.",
            "claim_type": "speculation",
            "independence_classification": "operator_assertion",
            "theory_group_id": "G2",
            "supports_theory_id": "T2U"
        }]
    }
    r = f9.process_intake(payload_a_inadmissible)
    print(f"Result: {r['status']} -> {r['results'][0]['status']}")

    # 3. Test Lane A (Inadmissible Independence)
    print("\n[Test 3] Injecting Lane A (Observation, but model_assertion)...")
    payload_a_model = {
        "source_entity": "Claude 3.5",
        "claims": [{
            "claim_text": "Based on the logs, T1 is flawed.",
            "claim_type": "observation",
            "independence_classification": "model_assertion",
            "theory_group_id": "G1",
            "supports_theory_id": "T1A"
        }]
    }
    r = f9.process_intake(payload_a_model)
    print(f"Result: {r['status']} -> {r['results'][0]['status']}")

    # 4. Test Lane A (Valid Admissible)
    print("\n[Test 4] Injecting Lane A (Valid Primary Observation)...")
    payload_a_valid = {
        "source_entity": "External_Sensor_Sys",
        "claims": [{
            "claim_text": "Error rate dropped by 4%.",
            "claim_type": "observation",
            "independence_classification": "primary",
            "theory_group_id": "G4",
            "supports_theory_id": "T4",
            "evidence_weight": 1.0
        }]
    }
    r = f9.process_intake(payload_a_valid)
    print(f"Result: {r['status']} -> {r['results'][0]['status']}")

    # 5. Check Ledgers
    print("\n[Final Ledgers Check]")
    print(f"Intake Envelope: {len(read_jsonl(f9.INTAKE_PATH))}")
    print(f"Quarantine: {len(read_jsonl(f9.QUARANTINE_PATH))}")
    print(f"Critiques: {len(read_jsonl(f9.CRITIQUES_PATH))}")
    print(f"F8 Market Observations: {len(read_jsonl(engine.OBSERVATIONS_PATH))}")

if __name__ == "__main__":
    test_f9()
