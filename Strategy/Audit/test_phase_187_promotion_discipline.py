import sys, os, json
sys.path.append(r"D:\infinite\Infinity\Strategy")
from strategy_engine import StrategyEngine

def test_promotion_discipline():
    print("\n[Phase 187: Promotion Discipline Test]")
    
    engine = StrategyEngine()
    engine.shadow_ledger = engine._load_shadow_ledger()
    
    claim = "The Cold Zero supersession correctly blocks phantom candidates from returning."
    entity = "phase_187_probe"
    
    # 1. Ingest benign system_probe claim
    engine.ingest_claim_candidate(
        entity=entity,
        claim=claim,
        source_id="test_probe_A",
        source_type="system_probe",
        confidence=0.9,
        artifact_type="observation",
        provenance_note="Phase 187 Initial"
    )
    
    # Run 21 cycles
    for _ in range(21):
        engine.run_once()
        
    candidates = engine.ecosystem_mapper._load_candidates()
    c_id = engine.ecosystem_mapper.get_claim_id(entity, claim)
    
    # 3. Confirm it remains BENIGN_OBSERVATION_PENDING
    status = candidates.get("candidates", {}).get(c_id, {}).get("status")
    if status == "BENIGN_OBSERVATION_PENDING":
        print("[PASS] Claim remains BENIGN_OBSERVATION_PENDING after >25 cycles.")
    else:
        print(f"[FAIL] Claim status is {status}")
        return
        
    # 4. Ingest exact same claim from same source_id
    engine.ingest_claim_candidate(
        entity=entity,
        claim=claim,
        source_id="test_probe_A",
        source_type="system_probe",
        confidence=0.9,
        artifact_type="observation",
        provenance_note="Phase 187 Duplicate"
    )
    
    for _ in range(5):
        engine.run_once()
        
    # 5. Confirm no promotion
    model = engine.ecosystem_mapper._load_model()
    if c_id in model.get("claims", {}):
        print("[FAIL] Claim promoted after identical source_id ingestion!")
        return
    else:
        print("[PASS] No promotion after identical source_id ingestion.")
        
    # 6. Ingest exact same claim from different source_type + source_id
    engine.node_id = "AXIS_NODE_REMOTE_02"
    engine.node_attestation = "21887bf7dfc54f3e318079d038d2074d_DIFFERENT"
    engine.ingest_claim_candidate(
        entity=entity,
        claim=claim,
        source_id="test_probe_B",
        source_type="factual_benchmark",
        confidence=0.9,
        artifact_type="observation",
        provenance_note="Phase 187 Corroboration"
    )
    
    # Run some cycles to allow promotion
    for _ in range(2):
        engine.run_once()
        
    # 7 & 8. Confirm promotion path
    model = engine.ecosystem_mapper._load_model()
    if c_id in model.get("claims", {}):
        print("[PASS] Claim successfully promoted after independent corroboration.")
    else:
        print("[FAIL] Claim NOT promoted after independent corroboration!")
        return
        
    # 9. Verify derivability
    candidates = engine.ecosystem_mapper._load_candidates()
    anomalies = engine.ecosystem_mapper._load_anomalies()
    
    ok, errs = engine.ecosystem_mapper.verify_state_derivability(
        model=model,
        receipt_dir=engine.receipt_dir,
        baseline_path=os.path.join(engine.ecosystem_mapper.state_dir, "ecosystem_model_baseline.json"),
        expected_baseline_hash=engine._load_shadow_ledger().get("baseline_model_hash"),
        current_candidates=candidates,
        current_anomalies=anomalies,
        expected_head=engine._load_shadow_ledger().get("ecosystem_receipts_head"),
        expected_cycle=engine._load_shadow_ledger().get("cycle_count")
    )
    
    if ok:
        print("[PASS] Derivability verified.")
    else:
        print("[FAIL] Derivability check failed.")
        for e in errs:
            print(e)
            
if __name__ == "__main__":
    test_promotion_discipline()
