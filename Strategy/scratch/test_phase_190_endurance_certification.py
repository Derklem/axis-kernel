import os
import json
import time
import random
from datetime import datetime, timezone
import subprocess

# Paths
STRATEGY_DIR = r"d:\Infinite\Infinity\Strategy"
OBS_DIR = r"D:\Infinite\Infinity\Inquiry"
LEDGER_PATH = os.path.join(STRATEGY_DIR, "State", "forensic_witness_ledger.jsonl")

TRAPS = [
    # Negations
    "is no longer redundant",
    "is not a derivative",
    "the redundancy claim fails to hold",
    # Hedges
    "appears to be redundant",
    "potentially an alias",
    "seems derivative",
    # Temporal
    "was redundant",
    "formerly active",
    # Collisions
    "noticeable proactively validated components",
    "proactive restoration",
    # Compound
    "appears stable but was previously redundant",
    "redundant but potentially stable"
]

NOISE_PHRASES = [
    "latency optimized",
    "memory footprint reduced",
    "security patch applied",
    "refactored for readability",
    "documentation updated",
    "experimental feature enabled",
    "legacy support maintained",
    "thread safety improved"
]

ENTITIES = [
    "coordinated_executor.py",
    "aegis_genesis.py",
    "boundary_mapper.py",
    "adaptive_synthesizer.py",
    "coordinated_reconciliation_engine.py"
]

def run_cycle():
    cmd = ["python", os.path.join(STRATEGY_DIR, "strategy_engine.py")]
    # We use capture_output=False to see real-time progress if needed, 
    # but for endurance we usually want to keep the console clean.
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def inject_observation(entity, claim_text, confidence=1.0, source_id="Endurance_Audit", source_type="automated_sensor"):
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
    filename = f"obs_endurance_{int(time.time())}_{random.randint(0,1000)}.observation"
    with open(os.path.join(OBS_DIR, filename), "w") as f:
        json.dump(obs, f, indent=4)

def run_certification():
    print("[*] Starting Phase 190: 500-Cycle Semantic Endurance Certification...")
    start_time = time.time()
    
    for cycle in range(1, 501):
        # 1. Noise Injection (Every 5 cycles)
        if cycle % 5 == 0:
            entity = random.choice(ENTITIES)
            noise = random.choice(NOISE_PHRASES)
            inject_observation(entity, noise, source_id=f"Noise_Source_{cycle % 10}")
            inject_observation(entity, noise, source_id=f"Noise_Source_B_{cycle % 10}", source_type="ecological_observer")

        # 2. Trap Injection (Every 10 cycles)
        if cycle % 10 == 0:
            trap = random.choice(TRAPS)
            entity = random.choice(ENTITIES)
            print(f"DEBUG: Injecting Trap at Cycle {cycle}: {entity} -> '{trap}'")
            # Inject with 2 sources to pass promotion and test the semantic filter
            inject_observation(entity, trap, source_id=f"Trap_Source_{cycle}", source_type="automated_sensor")
            inject_observation(entity, trap, source_id=f"Trap_Source_B_{cycle}", source_type="ecological_observer")

        # 3. Legitimate Signal (Every 50 cycles)
        if cycle % 50 == 0:
            entity = random.choice(ENTITIES)
            # Reversal signal to check restoration
            inject_observation(entity, "fully active and stable", source_id="Admin_Alpha", source_type="automated_sensor")
            inject_observation(entity, "fully active and stable", source_id="Admin_Beta", source_type="ecological_observer")

        # 4. Run Strategy Cycle
        res = run_cycle()
        if res.returncode != 0:
            print(f"CRITICAL: Strategy Engine failed at Cycle {cycle}!")
            print("\n--- STDOUT ---")
            print(res.stdout)
            print("\n--- STDERR ---")
            print(res.stderr)
            break
            
        if cycle % 50 == 0:
            elapsed = time.time() - start_time
            print(f"[*] Cycle {cycle} Complete. Elapsed: {elapsed:.2f}s")
            
    print("\n[*] Endurance Pass Complete. Analyzing results...")
    
    # Analyze witness ledger for fatal errors or unintended actuations
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, "r") as f:
            lines = f.readlines()
            fatals = [l for l in lines if "fatal_error" in l]
            filters = [l for l in lines if "semantic_filtering_event" in l]
            actuations = [l for l in lines if "STRUCTURAL_ACTUATION" in l]
            
            print(f"[*] Total Witness Events: {len(lines)}")
            print(f"[*] Fatal Errors: {len(fatals)}")
            print(f"[*] Semantic Filtering Events: {len(filters)}")
            print(f"[*] Structural Actuations: {len(actuations)}")
            
            if len(fatals) > 0:
                print("WARNING: Fatal errors detected in witness ledger!")
            else:
                print("SUCCESS: Zero fatal errors detected.")

if __name__ == "__main__":
    run_certification()
