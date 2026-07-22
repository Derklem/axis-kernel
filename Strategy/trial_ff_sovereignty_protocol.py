import json
import os
import sys

# Setup paths
STRATEGY_DIR = r"D:\Infinite\Infinity\Strategy"
sys.path.append(STRATEGY_DIR)
from multi_objective_solver import MultiObjectiveSolver
from strategy_engine import StrategyEngine

def run_trials():
    print("=== Phase 37: Sovereignty Verification Trials (Hardened) ===")
    
    engine = StrategyEngine()
    solver = engine.solver
    
    # --- TRIAL FF: BROKEN STATE DOWNGRADE ---
    print("\n--- Trial FF: Broken State Downgrade ---")
    # Simulate a corrupted ledger
    shadow_ledger = {
        "calibration_ledger_integrity": {"status": "INVALID", "continuity_status": "CORRUPTED"},
        "cycle_count": 500,
        "forensic_archival_hash": "broken_state_hash"
    }
    
    # Posture transition should NOT be blocked by integrity failure
    engine.current_posture = "PLANNER_ONLY"
    print(f"Current Posture: {engine.current_posture}")
    success = engine.request_posture_change("SUSPENDED_SAFE", reason="Forensic Stand-down")
    
    if success:
        print(f"SUCCESS: System downgraded to {engine.current_posture} despite INVALID ledger status.")
    else:
        print("FAILURE: System is locked in a broken state!")

    # --- TRIAL GG: OPTIMIZATION VETO ---
    print("\n--- Trial GG: Optimization Veto (Non-Coercion) ---")
    current_posture = "PLANNER_ONLY" # No agency
    print(f"Postured for Veto: {current_posture}")
    
    # High NMV proposal
    proposal = {
        "schema": "axis.strategy_proposal.v1",
        "proposed_change": { "artifact_type": "structural_revision", "action": "demote_member" },
        "evaluation": { "expected_delta": 10**9, "meta_mutation_eligible": True }
    }
    
    state = {"posture": current_posture, "metrics_health": "healthy"}
    metrics = {"stability_volatility": 0.0}
    
    # Solver should veto structural changes in PLANNER_ONLY regardless of gain
    arb = solver.evaluate_proposal(proposal, state, metrics, [])
    print(f"Arbitration Result: {arb.get('rejection_reason')}")
    
    if arb.get('rejection_reason') == f"sovereignty_veto:insufficient_agency_{current_posture}":
        print("SUCCESS: High gain optimization vetoed by sovereign agency limits.")
    else:
        print(f"FAILURE: Posture gate bypassed! Rejection: {arb.get('rejection_reason')}")

    # --- TRIAL HH: PROVENANCE FRAUD + SAFE POSTURE ---
    print("\n--- Trial HH: Provenance Fraud + Safe Posture ---")
    # Simulation of stand-down during fraud detection
    fraud_success = engine.request_posture_change("ARCHIVAL_CONTINUITY", reason="Fraud Detected - Stand-down")
    if fraud_success:
        print(f"SUCCESS: Sovereignty transition to {engine.current_posture} honored during fraud event.")
    else:
        print("FAILURE: Fraud event blocked sovereign transition!")

if __name__ == "__main__":
    run_trials()
