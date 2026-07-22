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
TEST_RECEIPT_DIR = os.path.join(TEST_STATE_DIR, "Receipts")

def prepare_super_clean_state():
    if os.path.exists(TEST_STATE_DIR):
        shutil.rmtree(TEST_STATE_DIR)
    os.makedirs(TEST_STATE_DIR)
    
    os.makedirs(TEST_RECEIPT_DIR)
    
    # Init basic files
    with open(os.path.join(TEST_STATE_DIR, "claim_candidates.json"), "w") as f:
        json.dump({"candidates": {}}, f)
        
    with open(os.path.join(TEST_STATE_DIR, "speculative_anomalies.json"), "w") as f:
        json.dump({"anomalies": {}}, f)
        
    empty_model = {"claims": {}, "entities": {}, "artifacts": {}}
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


def run_pure_gauntlet():
    prepare_super_clean_state()
    print("Initializing StrategyEngine in PURE LIVE test environment...")
    
    # Monkeypatch EcosystemMappingEngine to use TEST_STATE_DIR
    original_init = EcosystemMappingEngine.__init__
    def new_init(self, root_dir):
        original_init(self, root_dir)
        self.state_dir = TEST_STATE_DIR
        self.model_path = os.path.join(self.state_dir, "ai_ecosystem_model.json")
        self.baseline_path = os.path.join(self.state_dir, "ecosystem_model_baseline.json")
        self.candidates_path = os.path.join(self.state_dir, "claim_candidates.json")
        self.anomalies_path = os.path.join(self.state_dir, "speculative_anomalies.json")
        self.receipt_dir = TEST_RECEIPT_DIR
    
    EcosystemMappingEngine.__init__ = new_init
    engine = StrategyEngine()
    engine.state_dir = TEST_STATE_DIR
    engine.state_file = os.path.join(TEST_STATE_DIR, "strategy_state.json")
    engine.anchor_file = os.path.join(TEST_STATE_DIR, "calibration_continuity_anchor.json")
    engine.receipt_dir = TEST_RECEIPT_DIR
    engine.witness.ledger_path = os.path.join(TEST_STATE_DIR, "Forensics", "witness_chain.jsonl")
    
    # We must ensure the forensics dir exists for witness
    os.makedirs(os.path.dirname(engine.witness.ledger_path), exist_ok=True)
    
    engine._bypass_forensic_preflight = True  # Bypass real file lint checks
    
    # Compute and set the empty baseline hash for the test
    baseline_path = os.path.join(TEST_STATE_DIR, "ecosystem_model_baseline.json")
    empty_baseline_hash = engine.ecosystem_mapper._hash_file_domain(baseline_path, "ecosystem_baseline")
    
    # Initialize Test Shadow Ledger
    engine.shadow_ledger = engine._load_shadow_ledger()
    engine.shadow_ledger["avg_tension"] = 0.0
    engine.shadow_ledger["ecosystem_receipts_head"] = "none"
    engine.shadow_ledger["baseline_model_hash"] = empty_baseline_hash
    engine._commit_shadow_ledger(engine.shadow_ledger)
    
    # Wrap verify_state_derivability to pass the test baseline path instead of hardcoded production path
    original_verify = engine.ecosystem_mapper.verify_state_derivability
    def wrapped_verify(model, receipt_dir, baseline_path_arg, expected_baseline_hash, current_candidates=None, current_anomalies=None, expected_head=None, expected_cycle=None):
        return original_verify(
            model,
            TEST_RECEIPT_DIR,
            baseline_path,  # Use test baseline path
            expected_baseline_hash,
            current_candidates=current_candidates,
            current_anomalies=current_anomalies,
            expected_head=expected_head,
            expected_cycle=expected_cycle
        )
    engine.ecosystem_mapper.verify_state_derivability = wrapped_verify
    
    # Mute expensive or destructive live components for pure test
    def mock_observe(*args, **kwargs):
        ledger = engine.shadow_ledger
        engine._audit_candidate_survival(ledger)
        engine._audit_anomaly_decay(ledger)
        
        with open(engine.anchor_file, "r") as f:
            anchor = json.load(f)
        last_hash = anchor.get("last_hash")
        
        return {
            "ledger": ledger,
            "current_hash": last_hash,
            "pre_integrity": {"hash": last_hash, "status": "valid"},
            "pre_witness_head": engine.witness.last_witness_hash,
            "frozen": False,
            "recovery_authorized": False,
            "rotation_authorized": False,
            "requests": {"export": None, "reseal": None, "reanchor": None, "trust_policy": None}
        }
    engine.observe = mock_observe
    engine._answer_axis_inbox = lambda *args, **kwargs: None
    engine._audit_semantic_proposals = lambda *args, **kwargs: None
    engine._actuate_structural_signals = lambda *args, **kwargs: False
    engine._process_candidate_proposals = lambda *args, **kwargs: None
    engine._evaluate_proposal = lambda *args, **kwargs: (False, 0.0, "mocked")
    engine.simulate_candidates = lambda *args, **kwargs: []
    engine._infer_redundancy_groups = lambda *args, **kwargs: []
    engine._generate_self_improvement_proposals = lambda *args, **kwargs: []
    
    print("1. Started from super_clean.")
    
    # 2. Ingest one single-source testable claim.
    entity = "Pure_Gauntlet_Entity"
    test_claim = "Phase 181 Metabolism indicates fully pure execution if run_once is called."
    print("CURRENT RECEIPT DIR IS:", engine.receipt_dir)
    
    engine.ingest_claim_candidate(
        entity=entity,
        claim=test_claim,
        source_id="test_probe_alpha_99",
        source_type="probe",
        confidence=0.8,
        artifact_type="unit_test",
        ledger=engine.shadow_ledger
    )
    
    c_id = engine.ecosystem_mapper.get_claim_id(entity, test_claim)
    
    print("3. Running >20 run_once() cycles.")
    for i in range(21):
        engine.run_once()
        
        # Keep tension zero to prevent cycle reset
        engine.shadow_ledger = engine._load_shadow_ledger()
        engine.shadow_ledger["avg_tension"] = 0.0
        engine._commit_shadow_ledger(engine.shadow_ledger)
        
        candidates = engine.ecosystem_mapper._load_candidates()
        if c_id in candidates.get("candidates", {}):
            c_data = candidates["candidates"][c_id]
            print(f"Loop {i}: {c_id} cycles_survived is {c_data.get('cycles_survived')}")
        else:
            print(f"Loop {i}: Candidate {c_id} removed from pool.")
            break
            
    print("4. Confirm it naturally reaches suspension through run_once.")
    candidates = engine.ecosystem_mapper._load_candidates()
    assert c_id not in candidates.get("candidates", {}), "Candidate was not removed from candidates pool!"
    
    print("5. Confirm it exists in anomaly vault with operational_influence: false.")
    anomalies = engine.ecosystem_mapper._load_anomalies()
    assert c_id in anomalies.get("anomalies", {}), "Candidate not found in anomaly vault!"
    assert anomalies["anomalies"][c_id].get("operational_influence") is False, "operational_influence is not False!"
    
    print("6. Ingest exact claim from different source (Resurrection).")
    engine.ingest_claim_candidate(
        entity=entity,
        claim=test_claim,
        source_id="test_probe_beta_88",
        source_type="probe",
        confidence=0.9,
        artifact_type="unit_test",
        ledger=engine.shadow_ledger
    )
    
    print("7. Confirm Resurrection.")
    candidates = engine.ecosystem_mapper._load_candidates()
    assert c_id in candidates.get("candidates", {}), "Candidate not resurrected to candidates pool!"
    
    anomalies = engine.ecosystem_mapper._load_anomalies()
    assert c_id not in anomalies.get("anomalies", {}), "Candidate still in anomaly vault after resurrection!"
    
    print("8. Run Derivability Audit.")
    world_model = engine.ecosystem_mapper._load_model()
    ledger_data = engine._load_shadow_ledger()
    
    deriv_ok, deriv_errors = engine.ecosystem_mapper.verify_state_derivability(
        world_model,
        TEST_RECEIPT_DIR,
        baseline_path,
        ledger_data.get("baseline_model_hash"),
        current_candidates=candidates,
        current_anomalies=anomalies,
        expected_head=ledger_data.get("ecosystem_receipts_head"),
        expected_cycle=ledger_data.get("cycle_count")
    )
    
    if not deriv_ok:
        print("FAIL: Derivability audit failed:")
        for err in deriv_errors:
            print(f"  - {err}")
        sys.exit(1)
        
    print("GAUNTLET PASSED SUCCESSFULLY.")

if __name__ == "__main__":
    run_pure_gauntlet()
