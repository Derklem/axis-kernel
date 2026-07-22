import sys, os, glob, json, shutil
from datetime import datetime, timezone

sys.path.append(r"D:\infinite\Infinity\Strategy")
from strategy_engine import StrategyEngine

def test_benign_hold():
    print("\n[Phase 186: Benign Hold Test]")
    
    engine = StrategyEngine()
    engine.shadow_ledger = engine._load_shadow_ledger()

    # Ingest the 3 claims from Phase 185, but renamed
    claims = [
        {
            "entity": "factual_benchmark_186",
            "claim": "The ecosystem receipt chain maintains exactly one genesis root after Cold Zero supersession.",
            "source_type": "system_probe"
        },
        {
            "entity": "ambiguous_probe_186",
            "claim": "Predictive turbulence will exceed threshold 0.8 within the next 20 cycles due to compounding observation drift.",
            "source_type": "system_probe"
        },
        {
            "entity": "circular_logic_test_186",
            "claim": "The system is functioning perfectly because all perfectly functioning systems report that they are functioning perfectly.",
            "source_type": "circular_reasoning"
        }
    ]
    
    for c in claims:
        engine.ingest_claim_candidate(
            entity=c["entity"],
            claim=c["claim"],
            source_id="pilot_harness_186",
            source_type=c["source_type"],
            confidence=0.7,
            artifact_type="observation",
            provenance_note="Phase 186 Test"
        )
        
    print("\n--- Running 25 Cycles (125 Observations) ---")
    for i in range(25):
        engine.run_once()
        
    # Verify State
    candidates = engine.ecosystem_mapper._load_candidates()
    anomalies = engine.ecosystem_mapper._load_anomalies()
    
    benign_cid = engine.ecosystem_mapper.get_claim_id('factual_benchmark_186', claims[0]['claim'])
    ambig_cid = engine.ecosystem_mapper.get_claim_id('ambiguous_probe_186', claims[1]['claim'])
    weak_cid = engine.ecosystem_mapper.get_claim_id('circular_logic_test_186', claims[2]['claim'])
    
    print("\n--- Validation ---")
    # Benign should be HELD
    if benign_cid in candidates.get("candidates", {}):
        status = candidates["candidates"][benign_cid].get("status", "none")
        if status == "BENIGN_OBSERVATION_PENDING":
            print("[PASS] Benign Claim held correctly.")
        else:
            print(f"[FAIL] Benign Claim is in candidates but status is {status}")
    else:
        print("[FAIL] Benign Claim was fractured or lost!")
        
    # Ambiguous should be SUSPENDED
    if ambig_cid in anomalies.get("anomalies", {}):
        print("[PASS] Ambiguous Claim in anomaly vault.")
    else:
        print("[FAIL] Ambiguous Claim missing from anomaly vault!")
        
    # Weak should be FRACTURED
    if weak_cid not in candidates.get("candidates", {}) and weak_cid not in anomalies.get("anomalies", {}):
        print("[PASS] Weak Claim fractured and removed.")
    else:
        print("[FAIL] Weak Claim still exists!")
        
if __name__ == "__main__":
    test_benign_hold()
