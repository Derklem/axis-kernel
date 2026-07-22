import sys, os, json
sys.path.append(r"D:\infinite\Infinity\Strategy")
from strategy_engine import StrategyEngine

def test_knowledge_decay():
    print("\n[Phase 189: Knowledge Decay and Tombstone Test]")
    
    import time
    unique_id = int(time.time())
    claim = f"The Phase 189 tombstone system correctly retains historical revocation metadata - run {unique_id}."
    entity = f"phase_189_probe_{unique_id}"
    
    engine = StrategyEngine()
    engine.shadow_ledger = engine._load_shadow_ledger()
    
    c_id = engine.ecosystem_mapper.get_claim_id(entity, claim)
    
    # Pre-clean the environment just in case
    model = engine.ecosystem_mapper._load_model()
    if c_id in model.get("claims", {}):
        del model["claims"][c_id]
    if c_id in model.get("revoked_claims", {}):
        del model["revoked_claims"][c_id]
    engine.ecosystem_mapper._save_model(model)
    
    candidates = engine.ecosystem_mapper._load_candidates()
    if c_id in candidates.get("candidates", {}):
        del candidates["candidates"][c_id]
    engine.ecosystem_mapper._save_candidates(candidates)

    print("1. Injecting and Fast-Tracking a Claim into the World Model...")
    engine.ingest_claim_candidate(
        entity=entity,
        claim=claim,
        source_id="trusted_source_A",
        source_type="system_probe",
        confidence=0.9,
        artifact_type="observation",
        provenance_note="Phase 189 Setup"
    )
    
    # Give it independent quorum to promote immediately
    engine.node_id = "independent_node_B" # Bypass lineage entropy
    engine.ontology_seal = "independent_seal_B"
    engine.ingest_claim_candidate(
        entity=entity,
        claim=claim,
        source_id="trusted_source_B",
        source_type="factual_benchmark",
        confidence=0.9,
        artifact_type="observation"
    )
    
    print("2. Running 21 cycles to allow natural promotion...")
    for _ in range(21):
        engine.run_once()
        
    model = engine.ecosystem_mapper._load_model()
    if c_id not in model.get("claims", {}):
        print("[FAIL] Claim failed to promote naturally!")
        sys.exit(1)
        
    print("3. Emitting EPISTEMIC_CORRECTION receipt to drop confidence < 0.2")
    engine._emit_ecosystem_mutation_receipt(
        mutation_type="EPISTEMIC_CORRECTION",
        target_id=c_id,
        data={"reason": "test_backdoor", "new_confidence": 0.0},
        ledger=engine._load_shadow_ledger()
    )
    import os, glob, json
    receipt_files = glob.glob(os.path.join(engine.receipt_dir, "*.receipt"))
    newest = max(receipt_files, key=os.path.getmtime)
    with open(newest, "r") as f:
        receipt = json.load(f)
    model = engine.ecosystem_mapper._load_model()
    engine.ecosystem_mapper.apply_receipt_to_model(model, receipt)
    engine.ecosystem_mapper._save_model(model)
    
    # Mock derivability to avoid failing due to the backdoor
    original_verify = engine.ecosystem_mapper.verify_state_derivability
    engine.ecosystem_mapper.verify_state_derivability = lambda *args, **kwargs: (True, [])
        
    print("4. Running 6 cycles to trigger Phase 189 Persistence Decay...")
    for i in range(6):
        engine.run_once()
        model = engine.ecosystem_mapper._load_model()
        if c_id in model.get("revoked_claims", {}):
            print(f"DEBUG: Claim hit tombstone at cycle {i+1}")
            break

    model = engine.ecosystem_mapper._load_model()
    
    if c_id in model.get("claims", {}):
        print("[FAIL] Claim is still active in the World Model!")
        sys.exit(1)
        
    if c_id not in model.get("revoked_claims", {}):
        print("[FAIL] Claim was deleted but NOT tombstoned!")
        sys.exit(1)
        
    tombstone = model["revoked_claims"][c_id]
    print("[PASS] Claim safely decayed to tombstone.")
    print(json.dumps(tombstone, indent=2))
    
    if tombstone.get("resurrection_policy") != "blocked_pending_supermajority":
        print("[FAIL] Tombstone missing correct resurrection policy constraint.")
        sys.exit(1)
        
    print("3. Testing Resurrection Constraints...")
    engine.ingest_claim_candidate(
        entity=entity,
        claim=claim,
        source_id="HALCYON_ROOT",
        source_type="system_override",
        confidence=0.99,
        artifact_type="observation"
    )
    
    # Read candidates pool
    candidates = engine.ecosystem_mapper._load_candidates()
    cand = candidates.get("candidates", {}).get(c_id)
    
    if not cand:
        print("[FAIL] Resurrected claim was not routed to quarantine.")
        sys.exit(1)
        
    if cand.get("status") != "REASSERTED_AFTER_REVOCATION":
        print(f"[FAIL] Resurrected claim status incorrect: {cand.get('status')}")
        sys.exit(1)
        
    if cand.get("requires_supermajority") is not True:
        print("[FAIL] Resurrected claim does not require supermajority.")
        sys.exit(1)
        
    if cand.get("confidence", 1.0) > 0.4:
        print(f"[FAIL] Resurrected claim confidence cap breached: {cand.get('confidence')}")
        sys.exit(1)
        
    print("[PASS] Tombstoned claims re-enter with strict quarantine constraints.")

    print("4. Verifying State Derivability...")
    
    # Restore the original verify function
    engine.ecosystem_mapper.verify_state_derivability = original_verify
    expected_head = engine._load_shadow_ledger().get("ecosystem_receipts_head")
    expected_hash = engine._load_shadow_ledger().get("baseline_model_hash")
    model = engine.ecosystem_mapper._load_model()
    candidates = engine.ecosystem_mapper._load_candidates()
    ok, errs = engine.ecosystem_mapper.verify_state_derivability(
        model=model,
        receipt_dir=r"D:\infinite\Infinity\Strategy\State\Receipts",
        baseline_path=r"D:\infinite\Infinity\Strategy\State\ecosystem_model_baseline.json",
        expected_baseline_hash=expected_hash,
        current_candidates=candidates,
        expected_head=expected_head
    )
    
    if not ok:
        print(f"[FAIL] Derivability check failed: {errs}")
        sys.exit(1)
    
    print("[PASS] Full model is derivable including Tombstoned claims.")
    
    print("\nPhase 189: SEALED")

if __name__ == "__main__":
    test_knowledge_decay()
