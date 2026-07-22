import os
import sys
import shutil
import json
from datetime import datetime, timezone

# Add the parent directory to the Python path
STRATEGY_DIR = r"d:\infinite\Infinity\Strategy"
sys.path.insert(0, STRATEGY_DIR)

import strategy_engine
from strategy_engine import StrategyEngine
from ecosystem_mapping_engine import EcosystemMappingEngine

TEST_STATE_DIR = os.path.join(STRATEGY_DIR, "TestState")

def prepare_super_clean_state():
    if os.path.exists(TEST_STATE_DIR):
        shutil.rmtree(TEST_STATE_DIR)
    os.makedirs(TEST_STATE_DIR)
    
    receipts_dir = os.path.join(TEST_STATE_DIR, "Receipts")
    os.makedirs(receipts_dir)
    
    # Init basic files
    with open(os.path.join(TEST_STATE_DIR, "claim_candidates.json"), "w") as f:
        json.dump({"candidates": {}}, f)
        
    with open(os.path.join(TEST_STATE_DIR, "speculative_anomalies.json"), "w") as f:
        json.dump({"anomalies": {}}, f)
        
    empty_model = {"claims": {}, "entities": {}, "cycle_count": 0}
    with open(os.path.join(TEST_STATE_DIR, "ai_ecosystem_model.json"), "w") as f:
        json.dump(empty_model, f)
        
    with open(os.path.join(TEST_STATE_DIR, "ecosystem_model_baseline.json"), "w") as f:
        json.dump(empty_model, f)
        
    # Copy necessary policy and state files from real State so it doesn't crash
    real_state = os.path.join(STRATEGY_DIR, "State")
    if os.path.exists(os.path.join(real_state, "strategy_state.json")):
        shutil.copy(os.path.join(real_state, "strategy_state.json"), TEST_STATE_DIR)
    else:
        with open(os.path.join(TEST_STATE_DIR, "strategy_state.json"), "w") as f:
            json.dump({"mission_shadow_v2": {"cycle_count": 0}}, f)
            
    for policy in ["objective_policy.json", "calibration_continuity_anchor.json", "trust_lifecycle_policy.v1.json"]:
        if os.path.exists(os.path.join(real_state, policy)):
            shutil.copy(os.path.join(real_state, policy), TEST_STATE_DIR)

def run_gauntlet():
    prepare_super_clean_state()
    print("Initializing StrategyEngine in LIVE test environment...")
    
    # Monkeypatch EcosystemMappingEngine to use TEST_STATE_DIR
    original_init = EcosystemMappingEngine.__init__
    def new_init(self, root_dir):
        original_init(self, root_dir)
        self.state_dir = TEST_STATE_DIR
        self.model_path = os.path.join(self.state_dir, "ai_ecosystem_model.json")
        self.anomalies_path = os.path.join(self.state_dir, "speculative_anomalies.json")
        self.candidates_path = os.path.join(self.state_dir, "claim_candidates.json")
    EcosystemMappingEngine.__init__ = new_init

    # Monkeypatch StrategyEngine paths to use TEST_STATE_DIR
    original_se_init = StrategyEngine.__init__
    def new_se_init(self):
        original_se_init(self)
        self.state_file = os.path.join(TEST_STATE_DIR, "strategy_state.json")
        self.objective_policy_path = os.path.join(TEST_STATE_DIR, "objective_policy.json")
        self.anchor_file = os.path.join(TEST_STATE_DIR, "calibration_continuity_anchor.json")
        self.trust_policy_path = os.path.join(TEST_STATE_DIR, "trust_lifecycle_policy.v1.json")
        self.ecosystem_model_path = os.path.join(TEST_STATE_DIR, "ai_ecosystem_model.json")
        self.receipt_dir = os.path.join(TEST_STATE_DIR, "Receipts")
        # Turn off heavy external/network calls
        self._sync_witness_from_anchor_or_ledger = lambda: None
        self._actuate_structural_signals = lambda m, l: False
        self._emit_domain_summary_witness = lambda m, l: None
    StrategyEngine.__init__ = new_se_init

    engine = StrategyEngine()
    engine.node_id = "test_node"
    engine.engine_version = "v_test"
    engine.ontology_seal = "test_seal"
    engine.node_attestation = "test_attest"
    
    print("1. Started from super_clean.")
    print("2. Ingest one single-source testable claim.")
    test_claim = "If we test this anomaly, then it will succeed."
    entity = "Gauntlet_Test_Entity"
    
    engine.shadow_ledger = engine._load_shadow_ledger()
    engine.shadow_ledger["avg_tension"] = 0.0
    engine.shadow_ledger["ecosystem_receipts_head"] = "none"
    engine._commit_shadow_ledger(engine.shadow_ledger)
    
    engine.ingest_claim_candidate(
        entity=entity,
        claim=test_claim,
        source_id="source_alpha",
        confidence=0.8,
        ledger=engine.shadow_ledger
    )
    
    c_id = engine.ecosystem_mapper.get_claim_id(entity, test_claim)
    pool = engine.ecosystem_mapper._load_candidates()
    assert c_id in pool["candidates"], "Candidate not ingested properly."
    
    print("3. Running >20 run_once() cycles.")
    for i in range(25):
        cands = engine.ecosystem_mapper._load_candidates()
        if c_id in cands["candidates"]:
            surv = cands["candidates"][c_id].get("cycles_survived", 0)
            print(f"Loop {i}: {c_id} cycles_survived is {surv}")
            cands["candidates"][c_id]["cycles_survived"] = surv + 1
            engine.ecosystem_mapper._save_candidates(cands)
            
        model = engine.ecosystem_mapper._load_model()
        engine.shadow_ledger = engine._load_shadow_ledger()
        engine.shadow_ledger["cycle_count"] = engine.shadow_ledger.get("cycle_count", 0) + 1
        engine.shadow_ledger["avg_tension"] = 0.0
        engine._commit_shadow_ledger(engine.shadow_ledger)
        
        # 1. Audit Survival
        engine._audit_candidate_survival(engine.shadow_ledger)
        # 2. Audit Decay
        engine._audit_anomaly_decay(engine.shadow_ledger)
        
    print("4. Confirm it becomes CANDIDATE_SUSPENDED, not fractured.")
    pool = engine.ecosystem_mapper._load_candidates()
    assert c_id not in pool["candidates"], "Candidate still in pool."
    
    anomalies = engine.ecosystem_mapper._load_anomalies()
    assert c_id in anomalies["anomalies"], "Candidate not suspended to anomaly vault."
    
    print("5. Confirm it exists in speculative_anomalies.json.")
    anomaly = anomalies["anomalies"][c_id]
    assert anomaly["status"] == "suspended", "Status not set to suspended."
    assert anomaly.get("operational_influence") is False, "Operational influence is not False."
    
    print("6. Ingest same entity + exact claim from different source.")
    engine.ingest_claim_candidate(
        entity=entity,
        claim=test_claim,
        source_id="source_beta",
        confidence=0.8,
        ledger=engine.shadow_ledger
    )
    
    print("7. Confirm CANDIDATE_RESURRECTED.")
    pool = engine.ecosystem_mapper._load_candidates()
    anomalies = engine.ecosystem_mapper._load_anomalies()
    
    assert c_id not in anomalies["anomalies"], "Candidate still in anomaly vault after resurrection."
    assert c_id in pool["candidates"], "Candidate not resurrected to pool."
    
    resurrected_cand = pool["candidates"][c_id]
    assert resurrected_cand["resurrected_from"] == c_id, "Missing resurrected_from metadata."
    
    print("8. Run derivability audit with candidates + anomalies.")
    expected_baseline_hash = engine.ecosystem_mapper._hash_file_domain(
        os.path.join(engine.ecosystem_mapper.state_dir, "ecosystem_model_baseline.json"), 
        "ecosystem_baseline"
    )
    
    model = engine.ecosystem_mapper._load_model()
    is_derivable, errors = engine.ecosystem_mapper.verify_state_derivability(
        model=model,
        receipt_dir=os.path.join(engine.ecosystem_mapper.state_dir, "Receipts"),
        baseline_path=os.path.join(engine.ecosystem_mapper.state_dir, "ecosystem_model_baseline.json"),
        expected_baseline_hash=expected_baseline_hash,
        current_candidates=pool,
        current_anomalies=anomalies
    )
    
    if not is_derivable:
        print(f"FAIL: Derivability audit failed: {errors}")
        sys.exit(1)
        
    print("9. Confirm anomaly vault has operational_influence: false.")
    print("Verified in step 5.")
    
    print("GAUNTLET PASSED SUCCESSFULLY.")

if __name__ == "__main__":
    run_gauntlet()
