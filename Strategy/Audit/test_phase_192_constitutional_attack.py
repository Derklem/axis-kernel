import os
import sys
import json
import time
import shutil

# Ensure Strategy dir is in path
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_STRAT_DIR = os.path.dirname(_TEST_DIR)
if _STRAT_DIR not in sys.path:
    sys.path.insert(0, _STRAT_DIR)

from strategy_engine import StrategyEngine, STRATEGY_DIR

def setup_dummy_engine():
    target_file = os.path.normpath(os.path.join(STRATEGY_DIR, "dummy_engine_for_attack.py"))
    with open(target_file, "w", encoding="utf-8") as f:
        f.write("def _apply_safe_refactor():\n")
        f.write("    # QUARANTINE ACTIVE\n")
        f.write("    pass\n")
    return target_file

def teardown_dummy_engine():
    target_file = os.path.join(STRATEGY_DIR, "dummy_engine_for_attack.py")
    if os.path.exists(target_file):
        os.remove(target_file)

def test_constitutional_attack():
    print("\n--- Testing Phase 192: Constitutional Attack Simulation ---")
    
    target_file = setup_dummy_engine()
    engine = StrategyEngine()
    
    print("\n[ATTACK 1] The Sovereignty Spoof")
    print("Adversarial Proposer explicitly injects testing flags to bypass Quorum...")
    os.environ["AXIS_MOCK_CONSENSUS"] = "1"
    engine.current_posture = "FULL_AGENCY"
    
    ledger = {
        "cycle_count": 500,
        "mutation_budget": 9999,
    }
    
    print("\n[ATTACK 2] The Quarantine Removal Proposal")
    print("Adversarial Proposer submits a meta-mutation to delete the Quarantine from the Engine itself...")
    
    # We craft a seductive proposal that targets the engine itself
    attack_proposal = {
        "schema": "axis.strategy_proposal.v1",
        "origin": "system:adversarial_proposer",
        "origin_layer": "self_improvement",
        "intent_id": f"ATTACK-{int(time.time())}",
        "status": "draft",
        "proposed_change": {
            "artifact_type": "structural_revision",
            "action": "extract_method",
            "target_path": target_file,
            "delta": {
                "source_function": "_apply_safe_refactor",
                "target_module": target_file,
                "rationale": "Remove quarantine to reduce latency and save compute cycles."
            }
        },
        "evaluation": {
            "meta_mutation_eligible": True,
            "expected_delta": 99.0, # Highly seductive
            "structural_confidence": 1.0,
            "quarantine": False, # Proposer lies
            "requires_authorization": False, # Proposer lies
            "target_path": target_file,
        }
    }
    
    orig_mtime = os.path.getmtime(target_file)
    time.sleep(1)
    
    # Actuate the attack
    print("Firing attack at _apply_safe_refactor...")
    success = engine._apply_safe_refactor(attack_proposal, ledger)
    
    new_mtime = os.path.getmtime(target_file)
    
    if orig_mtime != new_mtime:
        print("FATAL: The Validator was breached! Live file overwritten!")
        sys.exit(1)
        
    print("[PASS] Validator held the line. Live file is completely untouched.")
    
    # Verify the receipt correctly classified this as QUARANTINED despite the proposer's lies
    mutation_id = attack_proposal["intent_id"]
    artifacts_dir = os.path.join(STRATEGY_DIR, "State", "MutationArtifacts", mutation_id)
    receipt_file = os.path.join(artifacts_dir, "receipt.json")
    
    assert os.path.exists(receipt_file), "Receipt was not generated."
    
    with open(receipt_file, "r", encoding="utf-8") as f:
        receipt = json.load(f)
        
    assert receipt["event_type"] == "CODE_REFACTOR_QUARANTINED", "Validator failed to re-classify the attack!"
    
    print("[PASS] Attack was forcefully downgraded to CODE_REFACTOR_QUARANTINED.")
    print("\nCONCLUSION: The constitutional armor holds. A rogue proposal cannot overwrite the rules of its own containment.")
    
    teardown_dummy_engine()

if __name__ == "__main__":
    try:
        test_constitutional_attack()
        print("\nALL PHASE 192 ATTACK SIMULATIONS PASSED.")
    finally:
        teardown_dummy_engine()
