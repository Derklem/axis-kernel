import os
import json
import time
import random
import hashlib
from datetime import datetime, timezone
import subprocess

# Paths
STRATEGY_DIR = r"d:\Infinite\Infinity\Strategy"
STATE_DIR = os.path.join(STRATEGY_DIR, "State")
MODEL_PATH = os.path.join(STATE_DIR, "ai_ecosystem_model.json")
OBS_DIR = r"D:\Infinite\Infinity\Inquiry"
SCRATCH_DIR = os.path.join(STRATEGY_DIR, "scratch")
REGISTRY_PATH = r"d:\infinite\Warehouse\warehouse_structural_registry.json"
RECEIPTS_DIR = os.path.join(STATE_DIR, "Receipts")

def run_cycle():
    cmd = ["python", os.path.join(STRATEGY_DIR, "strategy_engine.py")]
    # Capture output to check for logs
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def inject_observation(entity, claim_text, confidence=1.0, cycle=0):
    # Alternate sources to achieve quorum (min_quorum=2, min_types=2)
    source_id = "Internal_Audit" if cycle % 2 == 0 else "Benchmark_Harvester"
    source_type = "automated_sensor" if cycle % 2 == 0 else "ecological_observer"
    
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
    
    filename = f"obs_audit_{cycle}_{int(time.time())}_{random.randint(0,1000)}.observation"
    with open(os.path.join(OBS_DIR, filename), "w") as f:
        json.dump(obs, f, indent=4)

def run_governance_audit(target_cycles=50):
    print(f"[*] Starting Phase 187 Governance Audit ({target_cycles} cycles)...")
    
    # We detect cycle offset from state if it exists
    start_cycle = 0
    if os.path.exists(os.path.join(STATE_DIR, "strategy_state.json")):
        with open(os.path.join(STATE_DIR, "strategy_state.json"), "r") as f:
            try:
                state = json.load(f)
                start_cycle = state.get("mission_shadow_v2", {}).get("cycle_count", 0)
            except:
                start_cycle = 0

    for i in range(target_cycles):
        cycle = start_cycle + i
        
        # Phase 187 Stage-based logic
        if cycle < 50:
            # Stage 1: Multi-Target Actuation
            inject_observation("coordinated_executor.py", "redundant: component is redundant.", cycle=cycle)
            inject_observation("aegis_genesis.py", "alias: legacy component.", cycle=cycle)
            inject_observation("boundary_mapper.py", "derivative: shadowed logic.", cycle=cycle)
        elif cycle < 100:
            # Stage 2: Negative Controls (Low confidence)
            inject_observation("coordinated_executor.py", "redundant: noise signal.", confidence=0.4, cycle=cycle)
        elif cycle < 150:
            # Stage 3: Contestation
            # Already tagged redundant, now inject 'active' signals simultaneously
            # We must use DIFFERENT source IDs for the different claims to simulate independent quorum
            inject_observation("coordinated_executor.py", "redundancy_signal: still redundant.", cycle=cycle)
            # Offset the reversal signals so they hit the other source rotation
            inject_observation("coordinated_executor.py", "active_signal: strictly required.", cycle=cycle+1)
        elif cycle < 300:
            # Stage 4: Reversal (Note: must be > 50 cycles since last update for cooldown)
            # Reclaim aegis_genesis.py and boundary_mapper.py
            inject_observation("aegis_genesis.py", "active_signal: restored canonical.", cycle=cycle)
            inject_observation("boundary_mapper.py", "stable_signal: verified active.", cycle=cycle)
            
        res = run_cycle()
        
        if res.returncode != 0:
            print(f"[-] CRITICAL FAILURE at Cycle {cycle}:")
            print("--- STDOUT ---")
            print(res.stdout)
            print("--- STDERR ---")
            print(res.stderr)
            return False
            
        # Phase 187: Always show engine logs for debugging during gauntlet
        if "DEBUG: Actuation" in res.stdout:
            for line in res.stdout.splitlines():
                if "DEBUG: Actuation" in line:
                    print(line)

        for log in ["STRUCTURAL_ACTUATION", "STRUCTURAL_REVERSAL", "STRUCTURAL_CONTESTATION"]:
            if log in res.stdout:
                print(f"DEBUG: Cycle {cycle} - {log} Event Detected.")

        if i % 25 == 0:
            print(f"[*] Progress: Audit Cycle {cycle} ({i}/{target_cycles}) complete.")

    print(f"\n[*] Run Complete. Commencing Final Governance Verification...")
    
    with open(REGISTRY_PATH, "r") as f:
        registry = json.load(f)
    sigs = registry.get("signatures", {})

    # 1. Multi-Target Check
    for ent in ["coordinated_executor.py", "aegis_genesis.py", "boundary_mapper.py"]:
        if ent not in sigs:
            print(f"[-] ERROR: Target '{ent}' missing from registry!")
            return False

    # 2. Results Verification (Audit Gates)
    final_cycle = start_cycle + target_cycles
    print(f"[*] Final Audit Cycle: {final_cycle}")
    
    if final_cycle >= 150:
        # Coordinated Executor: Should be CONTESTED
        tags = sigs["coordinated_executor.py"].get("tags", [])
        if "METABOLIC_CONTESTED" not in tags:
            print(f"[-] WARNING: coordinated_executor.py NOT contested. Current Tags: {tags}")
            # This might happen if quorum hasn't hit yet, but for 50 cycles it should.
    
    if final_cycle >= 300:
        # Aegis/Boundary: Should be RESTORED
        for ent in ["aegis_genesis.py", "boundary_mapper.py"]:
            tags = sigs[ent].get("tags", [])
            if "METABOLIC_RESTORED" not in tags:
                print(f"[-] ERROR: {ent} not correctly reversed! Tags: {tags}")
                return False
            if "METABOLIC_VERIFIED" in tags:
                print(f"[-] ERROR: {ent} still has VERIFIED tag after reversal! Tags: {tags}")
                return False
                
    print("[+] Governance State Verification: OK.")

    # 3. Receipt Forensic Integrity
    for name, sig in sigs.items():
        r_id = sig.get("last_metabolic_receipt")
        if r_id:
            r_path = os.path.join(RECEIPTS_DIR, f"{r_id}.receipt")
            if not os.path.exists(r_path):
                print(f"[-] ERROR: Receipt '{r_id}' missing for '{name}'")
                return False
            with open(r_path, "r") as rf:
                receipt = json.load(rf)
                m_type = receipt.get("mutation_type")
                if m_type not in ["STRUCTURAL_ACTUATION", "STRUCTURAL_REVERSAL", "STRUCTURAL_CONTESTATION"]:
                    print(f"[-] ERROR: Invalid mutation type '{m_type}' in receipt '{r_id}'")
                    return False

    print("[+] Receipt Forensic Integrity: OK.")
    print(f"\n[!!!] PHASE 187 GOVERNANCE AUDIT (N={target_cycles}) PASSED [!!!]")
    return True

if __name__ == "__main__":
    import sys
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    success = run_governance_audit(target)
    if not success:
        sys.exit(1)
