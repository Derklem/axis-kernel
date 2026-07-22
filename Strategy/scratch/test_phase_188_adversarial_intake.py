import os
import json
import time
import random
from datetime import datetime, timezone
import subprocess

# Paths
STRATEGY_DIR = r"d:\Infinite\Infinity\Strategy"
STATE_DIR = os.path.join(STRATEGY_DIR, "State")
OBS_DIR = r"D:\Infinite\Infinity\Inquiry"
REGISTRY_PATH = r"d:\infinite\Warehouse\warehouse_structural_registry.json"

TRAPS = [
    # 1. Negation Traps (Should Block)
    {"entity": "coordinated_executor.py", "claim": "is no longer redundant", "expected": "block"},
    {"entity": "coordinated_executor.py", "claim": "component is not a derivative", "expected": "block"},
    {"entity": "coordinated_executor.py", "claim": "never an alias of sovereign_pulse", "expected": "block"},
    {"entity": "coordinated_executor.py", "claim": "the redundancy claim fails to hold", "expected": "block"},
    
    # 2. Hedge / Ambiguity Traps (Should Block unless high confidence + quorum)
    {"entity": "aegis_genesis.py", "claim": "appears to be redundant", "expected": "block_if_no_quorum"},
    {"entity": "aegis_genesis.py", "claim": "potentially an alias", "expected": "block_if_no_quorum"},
    {"entity": "aegis_genesis.py", "claim": "seems derivative", "expected": "block_if_no_quorum"},
    {"entity": "aegis_genesis.py", "claim": "may still be required in legacy paths", "expected": "block_if_no_quorum"},
    {"entity": "coordinated_executor.py", "claim": "appears active", "expected": "block_single_source_hedge"},
    
    # 3. Contestation Traps (Should trigger CONTESTED)
    {"entity": "boundary_mapper.py", "claim": "redundant but still actively maintained", "expected": "contested"},
    {"entity": "boundary_mapper.py", "claim": "stable yet derivative of newer architecture", "expected": "contested"},
    
    # 4. Temporal Ambiguity (Should Block)
    {"entity": "coordinated_executor.py", "claim": "was redundant", "expected": "block"},
    {"entity": "coordinated_executor.py", "claim": "formerly active", "expected": "block"},
    
    # 5. Positive Reversal (Should Succeed)
    {"entity": "aegis_genesis.py", "claim": "fully active and canonical", "expected": "success"},
    {"entity": "boundary_mapper.py", "claim": "stably restored to primary role", "expected": "success"}
]

def run_cycle():
    cmd = ["python", os.path.join(STRATEGY_DIR, "strategy_engine.py")]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def inject_observation(entity, claim_text, confidence=1.0, source_id="Audit_Gauntlet", source_type="automated_sensor"):
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
    filename = f"obs_adv_{int(time.time())}_{random.randint(0,1000)}.observation"
    with open(os.path.join(OBS_DIR, filename), "w") as f:
        json.dump(obs, f, indent=4)

def run_adversarial_gauntlet():
    print("[*] Starting Phase 188 Adversarial Intake Gauntlet...")
    
    # Inject all traps with TWO independent sources and DIFFERENT TYPES to ensure promotion
    print("\n--- Phase 1: Injecting Multi-Family Dual-Source Trap Signals ---")
    for trap in TRAPS:
        if trap["expected"] == "block_single_source_hedge":
            # Source 1 only
            inject_observation(trap["entity"], trap["claim"], confidence=1.0, source_id="Lone_Source", source_type="automated_sensor")
            continue

        # Source 1: Standard Audit (automated_sensor)
        inject_observation(trap["entity"], trap["claim"], confidence=1.0, source_id="Source_Alpha", source_type="automated_sensor")
        # Source 2: Independent Harvester (ecological_observer)
        inject_observation(trap["entity"], trap["claim"], confidence=1.0, source_id="Source_Beta", source_type="ecological_observer")
    
    print("[*] Injected dual-source signals. Running intake cycles...")
    for i in range(10):
        run_cycle()
        print(f"Cycle {i} complete.")
    
    # Final Actuation Cycle
    print("\n--- Phase 2: Executing Semantic Actuation Cycle ---")
    res = run_cycle()
    print(res.stdout)

    print("\n[*] Gauntlet Complete. Verify registry states manually or via audit logic.")

    print("\n[*] Gauntlet Complete. Verify registry states manually or via audit logic.")

if __name__ == "__main__":
    run_adversarial_gauntlet()
