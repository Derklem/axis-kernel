import json
import time
import os

STATE_FILE = r"d:\infinite\Infinity\Strategy\State\strategy_state.json"
STRATEGY_HASH = "7bf5a5c5f8bb76301bb5e0086747791f3ee116afcb8f4f32471df081dcf40ead"
BASELINE_HASH = "5875833717a5ae06df63db3506928c260476c010be6178caca51984997c54e95"
LINT_HASH = "3dab239d0a695818ca00f5861b7fbc7f2bc00165df7852eccf47366870a06730"

def inject_request():
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
    ledger = state.get("mission_shadow_v2", {})
    
    # Get current witness head
    sys.path.append(r"d:\infinite\Infinity\Strategy")
    from strategy_engine import StrategyEngine
    head = StrategyEngine().witness.verify_chain()
    
    request = {
        "status": "pending",
        "operator": "HALCYON_ROOT",
        "nonce": f"harden_sync_{int(time.time())}",
        "reason": "Phase 172 External Intake Fracture Gate",
        "mode": "forensic_repair",
        "scope": "temporal_continuity",
        "acknowledge_lineage_break": True,
        "requested_cycle": ledger.get("cycle_count", 0),
        "expires_cycle": ledger.get("cycle_count", 0) + 10,
        "witness_repair_head": head,
        "new_core_hashes": {
            "strategy_engine": STRATEGY_HASH,
            "lint_engine": LINT_HASH,
            "baseline_model": BASELINE_HASH
        }
    }
    ledger["continuity_reanchor_request"] = request
    state["mission_shadow_v2"] = ledger
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)
    print(f"[*] Injected re-anchor for Phase 172 (Head: {head[:12]})")

if __name__ == "__main__":
    import sys
    inject_request()
