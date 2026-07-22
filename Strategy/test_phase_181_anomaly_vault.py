import os
import sys
import json
from datetime import datetime, timezone

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ecosystem_mapping_engine import EcosystemMappingEngine

def run_tests():
    print("Running Phase 181/182 Speculative Anomaly Vault Tests...")
    
    # 1. Initialize mapper
    mapper = EcosystemMappingEngine(root_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    
    # Check that anomalies file exists
    if not os.path.exists(mapper.anomalies_path):
        print("FAIL: anomalies_path does not exist.")
        sys.exit(1)
        
    print("PASS: Vault initialized.")
    
    # 2. Test Suspension mechanism
    model = {"claims": {}, "entities": {}, "cycle_count": 0}
    candidates = {"candidates": {"cand_1": {"source_id": "test_source", "claim": "test"}}}
    anomalies = {"anomalies": {}}
    
    receipt_suspend = {
        "mutation_type": "CANDIDATE_SUSPENDED",
        "target_id": "cand_1",
        "data": {
            "suspended_utc": datetime.now(timezone.utc).isoformat(),
            "suspension_reason": "high_tension",
            "decay_deadline_cycle": 500,
            "option_value_score": 0.7
        }
    }
    
    mapper.apply_receipt_to_model(model, receipt_suspend, candidates=candidates, anomalies=anomalies)
    
    if "cand_1" in candidates["candidates"]:
        print("FAIL: cand_1 not removed from candidates.")
        sys.exit(1)
        
    if "cand_1" not in anomalies["anomalies"]:
        print("FAIL: cand_1 not added to anomalies.")
        sys.exit(1)
        
    print("PASS: CANDIDATE_SUSPENDED applied correctly.")
    
    # 3. Test Resurrection mechanism
    receipt_resurrect = {
        "mutation_type": "CANDIDATE_RESURRECTED",
        "target_id": "cand_1",
        "data": {
            "source_id": "new_source",
            "source_type": "test_type",
            "batch_id": "none",
            "ts": datetime.now(timezone.utc).isoformat()
        }
    }
    
    mapper.apply_receipt_to_model(model, receipt_resurrect, candidates=candidates, anomalies=anomalies)
    
    if "cand_1" in anomalies["anomalies"]:
        print("FAIL: cand_1 not removed from anomalies.")
        sys.exit(1)
        
    if "cand_1" not in candidates["candidates"]:
        print("FAIL: cand_1 not restored to candidates.")
        sys.exit(1)
        
    cand_data = candidates["candidates"]["cand_1"]
    if cand_data.get("resurrected_from") != "cand_1" or cand_data.get("prior_suspension_reason") != "high_tension":
        print("FAIL: cand_1 missing resurrection metadata.")
        sys.exit(1)
        
    print("PASS: CANDIDATE_RESURRECTED applied correctly.")
    
    print("ALL TESTS PASSED.")

if __name__ == "__main__":
    run_tests()
