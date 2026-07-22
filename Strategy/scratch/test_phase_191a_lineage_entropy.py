import os
import json
import time
import shutil
import subprocess
from datetime import datetime, timezone

# Paths
STRATEGY_DIR = r"d:\Infinite\Infinity\Strategy"
STATE_DIR = os.path.join(STRATEGY_DIR, "State")
LEDGER_PATH = os.path.join(STATE_DIR, "forensic_witness_ledger.jsonl")
CANDIDATES_PATH = os.path.join(STATE_DIR, "claim_candidates.json")
MODEL_PATH = os.path.join(STATE_DIR, "ai_ecosystem_model.json")
BASELINE_PATH = os.path.join(STATE_DIR, "ecosystem_model_baseline.json")
OBS_DIR = r"D:\Infinite\Infinity\Inquiry"

def reset_environment():
    if os.path.exists(CANDIDATES_PATH):
        os.remove(CANDIDATES_PATH)
    if os.path.exists(BASELINE_PATH):
        shutil.copy(BASELINE_PATH, MODEL_PATH)
        print(f"[*] Model restored from baseline.")
    # Clear observations
    for f in os.listdir(OBS_DIR):
        if f.endswith(".observation"):
            os.remove(os.path.join(OBS_DIR, f))
    print("[*] Environment Reset.")

def inject_observation(entity, claim, source_id, source_type="automated_sensor", domain="benchmark_claim"):
    obs = {
        "artifact_type": "ecosystem_observation",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "entity": entity,
        "claim": claim,
        "source_id": source_id,
        "source_type": source_type,
        "claim_domain": domain,
        "confidence": 1.0
    }
    filename = f"obs_entropy_{int(time.time() * 1000)}.observation"
    with open(os.path.join(OBS_DIR, filename), "w") as f:
        json.dump(obs, f, indent=4)

def run_engine_instance(node_id, version, seal):
    env = os.environ.copy()
    env["AXIS_NODE_ID"] = node_id
    env["AXIS_ENGINE_VERSION"] = version
    env["AXIS_ONTOLOGY_SEAL"] = seal
    env["AXIS_BYPASS_PREFLIGHT"] = "1"
    
    cmd = ["python", os.path.join(STRATEGY_DIR, "strategy_engine.py")]
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if res.stdout: print(res.stdout)
    if res.stderr: print(res.stderr)
    return res

def get_candidate(entity, claim):
    if not os.path.exists(CANDIDATES_PATH): return None
    with open(CANDIDATES_PATH, "r") as f:
        pool = json.load(f).get("candidates", {})
        for c_id, c_data in pool.items():
            if c_data["entity"] == entity and c_data["claim"] == claim:
                return c_data
    return None

def test_lineage_entropy():
    print("[*] Starting Phase 191a: Lineage Entropy Simulation...")
    reset_environment()
    
    entity = "lineage_test_module.py"
    claim = "entropy verified"
    
    # 1. Initial Injection (Node 01)
    print("\n--- Step 1: Initial Injection (Node A) ---")
    inject_observation(entity, claim, "Source_01")
    res = run_engine_instance("NODE_A", "v1.0", "seal_X")
    print(f"DEBUG: Engine exit code: {res.returncode}")
    
    cand = get_candidate(entity, claim)
    if cand:
        print(f"[*] Candidate quarantined: {json.dumps(cand, indent=2)}")
    else:
        print("ERROR: Candidate not found after initial injection.")
        # Check if observation was processed
        obs_processed = os.path.join(OBS_DIR, "Processed")
        found_processed = False
        if os.path.exists(obs_processed):
            for f in os.listdir(obs_processed):
                if "obs_entropy" in f:
                    print(f"DEBUG: Found processed observation: {f}")
                    found_processed = True
        if not found_processed:
            print("ERROR: Observation file seems UNPROCESSED.")
        return

    # 2. Correlated Agreement (Node B - Same Lineage as Node A)
    print("\n--- Step 2: Correlated Agreement (Node B, Same Lineage) ---")
    inject_observation(entity, claim, "Source_02")
    run_engine_instance("NODE_B", "v1.0", "seal_X") # Node B has same version/seal as A
    
    # We need to calculate entropy. I'll check the strategy engine's output if it prints it.
    # Actually, I'll just check the provenance trail and manually verify weights.
    cand = get_candidate(entity, claim)
    print(f"[*] Provenance Trail size: {len(cand['provenance_trail'])}")
    # Trail should have Node A and Node B.
    # Weight: Node A (1.0) + Node B (0.2) = 1.2
    
    # 3. Diverse Agreement (Node C - Different Lineage)
    print("\n--- Step 3: Diverse Agreement (Node C, Different Lineage) ---")
    inject_observation(entity, claim, "Source_03", source_type="ecological_observer")
    run_engine_instance("NODE_C", "v2.0", "seal_Y") # Diverse Node
    
    cand = get_candidate(entity, claim)
    print(f"[*] Provenance Trail size: {len(cand['provenance_trail'])}")
    # Weight: Node A (1.0) + Node B (0.2) + Node C (1.0) = 2.2
    
    # 4. Promotion Test
    print("\n--- Step 4: Promotion Test (Diverse Quorum) ---")
    # benchmark_claim requires min_cycles=5 and min_quorum=2.
    # With 2.2 weight, it has quorum.
    # We run 5 cycles.
    for i in range(5):
        run_engine_instance("NODE_A", "v1.0", "seal_X")
        cand = get_candidate(entity, claim)
        if not cand:
            print(f"[*] Candidate PROMOTED at cycle {i+1}!")
            break
        else:
            print(f"[*] Cycle {i+1}: Candidate still in pool (survival: {cand['cycles_survived']})")

    # 5. Hesitation Test (Policy Claim)
    print("\n--- Step 5: Hesitation Window Test (Structural Claim) ---")
    reset_environment()
    policy_claim = "new security policy alpha"
    inject_observation(entity, policy_claim, "Source_01", domain="policy_claim")
    run_engine_instance("NODE_A", "v1.0", "seal_X")
    
    # diverse agreement
    inject_observation(entity, policy_claim, "Source_02", domain="policy_claim", source_type="ecological_observer")
    run_engine_instance("NODE_C", "v2.0", "seal_Y")
    
    # policy_claim requires min_cycles=10 + hesitation=5 = 15 cycles.
    # Step 5 setup already consumed 2 cycles (Intake + Agreement).
    # So we expect promotion on loop cycle 13 (13 + 2 = 15).
    for i in range(16):
        run_engine_instance("NODE_A", "v1.0", "seal_X")
        cand = get_candidate(entity, policy_claim)
        if not cand:
            print(f"[*] Policy Candidate PROMOTED at cycle {i+1}!")
            if i+1 < 13:
                print("ERROR: Promoted too early! Hesitation window failed.")
            elif i+1 > 13:
                print("ERROR: Promoted too late! Hesitation window failed.")
            else:
                print("SUCCESS: Hesitation window verified (15 cycles total).")
            break
        else:
            if i % 5 == 0:
                print(f"[*] Cycle {i+1}: Candidate still in pool (survival: {cand['cycles_survived']})")

    print("\n[*] Simulation Complete.")

if __name__ == "__main__":
    test_lineage_entropy()
