import os
import sys
import json
import time

# Ensure Strategy dir is in path
STRATEGY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if STRATEGY_DIR not in sys.path:
    sys.path.insert(0, STRATEGY_DIR)

from strategy_engine import StrategyEngine

def setup_dummy_file():
    target_file = os.path.join(STRATEGY_DIR, "dummy_debt.py")
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("def oversized_func():\n")
        for i in range(150):
            f.write(f"    x_{i} = {i}\n")
        f.write("    return sum([x_0, x_1])\n")
    return target_file

def teardown_dummy_file():
    target_file = os.path.join(STRATEGY_DIR, "dummy_debt.py")
    if os.path.exists(target_file):
        os.remove(target_file)

def test_read_only_gauntlet():
    print("\n--- Testing Phase 191: Read-Only Self-Improvement Gauntlet ---")
    
    os.environ["AXIS_MOCK_CONSENSUS"] = "1"
    
    target_file = setup_dummy_file()
    engine = StrategyEngine()
    engine.current_posture = "FULL_AGENCY"
    
    # 1. Inject structural debt
    ledger = {
        "cycle_count": 100,
        "mutation_budget": 10,
        "last_mutation_cycle": 0,
        "idle_cycles": 50,
        "high_debt_functions": [
            {
                "id": "dummy_debt.py::oversized_func",
                "file": "dummy_debt.py",
                "function": "oversized_func",
                "lines": 155,
                "debt_type": "oversized"
            }
        ]
    }
    
    # 2. Generate Proposal
    proposals = engine._generate_self_improvement_proposals(ledger)
    assert len(proposals) > 0, "Expected at least one proposal"
    
    prop = proposals[0]
    eval_block = prop.get("evaluation", {})
    
    # 3. Assert Quarantine Status
    assert eval_block.get("quarantine") is True, "Proposal MUST be quarantined by default."
    assert eval_block.get("requires_authorization") is True, "Proposal MUST require external authorization."
    print("[PASS] Phase 191 Proposal correctly generated with strict quarantine defaults.")
    
    # 4. Dry Run / Execute Safe Refactor
    # We pass the proposal directly to _apply_safe_refactor
    # Even though it is "authorized" via mock consensus, it should NOT mutate the live file.
    
    # Record original file modification time
    orig_mtime = os.path.getmtime(target_file)
    
    time.sleep(1) # Ensure time difference if it gets modified
    
    # Run the safe refactor flow
    success = engine._apply_safe_refactor(prop, ledger)
    assert success is True, "The safe refactor flow should complete the quarantine successfully."
    
    # Verify the target file was NOT overwritten
    new_mtime = os.path.getmtime(target_file)
    assert orig_mtime == new_mtime, "FATAL: The target file was modified! The gauntlet failed to hold the refactor."
    
    print("[PASS] Target file was NOT modified. Automatic application is blocked.")
    
    # 5. Verify the artifacts were created
    mutation_id = prop.get("intent_id")
    artifacts_dir = os.path.join(STRATEGY_DIR, "State", "MutationArtifacts", mutation_id)
    
    assert os.path.exists(artifacts_dir), "Mutation artifacts directory not created"
    
    patch_file = os.path.join(artifacts_dir, "patch.diff")
    receipt_file = os.path.join(artifacts_dir, "receipt.json")
    
    assert os.path.exists(patch_file), "patch.diff was not generated"
    assert os.path.exists(receipt_file), "receipt.json was not generated"
    
    with open(receipt_file, "r", encoding="utf-8") as f:
        receipt = json.load(f)
        
    assert receipt["event_type"] == "CODE_REFACTOR_QUARANTINED", "Receipt type should be QUARANTINED, not APPLIED"
    
    print("[PASS] Patch diff generated and strictly quarantined in MutationArtifacts.")
    print("[PASS] Read-Only Gauntlet proves Validator > Proposer.")
    
    teardown_dummy_file()

if __name__ == "__main__":
    try:
        test_read_only_gauntlet()
        print("\nALL PHASE 191 GAUNTLET TESTS PASSED.")
    finally:
        teardown_dummy_file()
