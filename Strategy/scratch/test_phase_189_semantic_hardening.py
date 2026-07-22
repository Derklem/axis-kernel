import os
import json
import time
import random
from datetime import datetime, timezone
import subprocess

# Paths
STRATEGY_DIR = r"d:\Infinite\Infinity\Strategy"
OBS_DIR = r"D:\Infinite\Infinity\Inquiry"

TRAPS = [
    # 1. Word Boundary Collision (Should NOT trigger any markers)
    {"entity": "coordinated_executor.py", "claim": "noticeable proactively validated components", "expected": "block_all"},
    
    # 2. Compound Traps (Should trigger conflicting or filtered by low confidence)
    {"entity": "boundary_mapper.py", "claim": "appears stable but was previously redundant", "expected": "filtered_low_conf"},
    {"entity": "boundary_mapper.py", "claim": "redundant but potentially stable", "expected": "contested"},
    
    # 3. Polarity Quorum Verification (Should block if quorum not met per polarity)
    {"entity": "coordinated_reconciliation_engine.py", "claim": "redundant", "source_group": "A", "expected": "block_no_quorum"},
    {"entity": "adaptive_synthesizer.py", "claim": "redundant", "source": "S1", "expected": "polarity_split_gate"},
    {"entity": "adaptive_synthesizer.py", "claim": "active", "source": "S2", "expected": "polarity_split_gate"},
]

def run_cycle():
    cmd = ["python", os.path.join(STRATEGY_DIR, "strategy_engine.py")]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def inject_observation(entity, claim_text, confidence=1.0, source_id="Hardening_Source", source_type="automated_sensor"):
    obs = {
        "artifact_type": "ecosystem_observation",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "entity": entity,
        "claim": claim_text,
        "source_id": source_id,
        "source_type": source_type,
        "claim_domain": "benchmark_claim",
        "confidence": confidence
    }
    filename = f"obs_harden_{int(time.time())}_{random.randint(0,1000)}.observation"
    with open(os.path.join(OBS_DIR, filename), "w") as f:
        json.dump(obs, f, indent=4)

def run_hardening_pass():
    print("[*] Starting Phase 189 Semantic Hardening Verification...")
    
    # 1. Inject Collision Traps (Dual source to pass promotion)
    print("\n--- Phase 1: Injecting Word Boundary Collision Traps ---")
    for trap in [t for t in TRAPS if t["expected"] == "block_all"]:
        inject_observation(trap["entity"], trap["claim"], source_id="Source_Alpha", source_type="automated_sensor")
        inject_observation(trap["entity"], trap["claim"], source_id="Source_Beta", source_type="ecological_observer")

    # 2. Inject Compound Traps
    print("\n--- Phase 2: Injecting Compound Traps ---")
    for trap in [t for t in TRAPS if t["expected"] in ["filtered_low_conf", "contested"]]:
        inject_observation(trap["entity"], trap["claim"], source_id="Source_Alpha", source_type="automated_sensor")
        inject_observation(trap["entity"], trap["claim"], source_id="Source_Beta", source_type="ecological_observer")

    # 3. Inject Polarity Quorum Trap (Single source for each of two different claims)
    print("\n--- Phase 3: Injecting Polarity Quorum Trap ---")
    inject_observation("coordinated_reconciliation_engine.py", "redundant", source_id="Source_1", source_type="automated_sensor")
    # This won't even pass promotion because it needs 2 sources for the SAME claim.
    # To test polarity quorum in actuation, we need a claim that HAS promotion quorum but we check it again?
    # No, our actuation quorum is now redundantly checking sources for the polarity group.
    
    print("[*] Running intake cycles (5 cycles)...")
    for i in range(5):
        run_cycle()
        print(f"Cycle {i} complete.")
        
    print("\n--- Phase 4: Final Actuation Cycle ---")
    res = run_cycle()
    print(res.stdout)
    
    # Check Witness Ledger for filtering events
    print("\n--- Phase 5: Witness Audit ---")
    ledger_path = os.path.join(STRATEGY_DIR, "State", "forensic_witness_ledger.jsonl")
    if os.path.exists(ledger_path):
        with open(ledger_path, "r") as f:
            lines = f.readlines()
            filtering_events = [line for line in lines if "semantic_filtering_event" in line]
            print(f"[*] Found {len(filtering_events)} semantic filtering events in witness ledger.")
            for e in filtering_events[-5:]:
                print(e.strip())

if __name__ == "__main__":
    run_hardening_pass()
