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
    filename = f"obs_attest_{int(time.time() * 1000)}.observation"
    with open(os.path.join(OBS_DIR, filename), "w") as f:
        json.dump(obs, f, indent=4)

def run_engine_instance(node_id, version, seal, bypass_preflight=True):
    env = os.environ.copy()
    env["AXIS_NODE_ID"] = node_id
    env["AXIS_ENGINE_VERSION"] = version
    env["AXIS_ONTOLOGY_SEAL"] = seal
    if bypass_preflight:
        env["AXIS_BYPASS_PREFLIGHT"] = "1"
    
    cmd = ["python", os.path.join(STRATEGY_DIR, "strategy_engine.py")]
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return res

def get_candidate(entity, claim):
    if not os.path.exists(CANDIDATES_PATH): return None
    with open(CANDIDATES_PATH, "r") as f:
        pool = json.load(f).get("candidates", {})
        for c_id, c_data in pool.items():
            if c_data["entity"] == entity and c_data["claim"] == claim:
                return c_data
    return None

def test_attested_diversity():
    print("[*] Starting Phase 191b: Attested Diversity Simulation...")
    reset_environment()
    
    entity = "attestation_test_module.py"
    claim = "attestation verified"
    
    # 1. Initial Injection (Node A)
    print("\n--- Step 1: Initial Injection (Node A) ---")
    inject_observation(entity, claim, "Source_01")
    run_engine_instance("NODE_A", "v1.9.1", "seal_X")
    
    cand = get_candidate(entity, claim)
    if cand:
        print(f"[*] Candidate quarantined. Provenance count: {len(cand['provenance_trail'])}")
        print(f"[*] Attestation Hash: {cand['provenance_trail'][0]['lineage']['node_attestation'][:12]}")
    else:
        print("ERROR: Candidate not found.")
        return

    # 2. Spoofing Attempt (Node B - Same Code, but different Version string)
    print("\n--- Step 2: Spoofing Attempt (Node B, Same Code, Spoofed Version) ---")
    inject_observation(entity, claim, "Source_02")
    run_engine_instance("NODE_B", "Spoofed-v9.9.9", "seal_X") 
    
    cand = get_candidate(entity, claim)
    # Both A and B have same code, so same attestation.
    # Provenance trail should show both.
    # Entropy should penalize B.
    print(f"[*] Provenance Trail size: {len(cand['provenance_trail'])}")
    lineage_a = cand['provenance_trail'][0]['lineage']
    lineage_b = cand['provenance_trail'][1]['lineage']
    
    if lineage_a['node_attestation'] == lineage_b['node_attestation']:
        print(f"[*] SUCCESS: Attestation match detected despite version spoof ({lineage_b['engine_version']})")
    else:
        print("ERROR: Attestation mismatch on identical code!")
        return

    # 3. diverse Agreement (Node C - Different Code/Policy?)
    # Since we can't easily change the code in the middle of a test, 
    # we'll simulate a diverse node by passing a different attestation hash via env.
    print("\n--- Step 3: Diverse Agreement (Node C, Diverse Attestation) ---")
    inject_observation(entity, claim, "Source_03", source_type="ecological_observer")
    
    # We'll use a hack: set AXIS_ONTOLOGY_SEAL to something different to simulate diverse rules
    # and we'll also override node_attestation if we add an env var for it.
    
    # Actually, I haven't added an env override for node_attestation yet.
    # I'll just change the ontology seal which is part of the grouping key.
    run_engine_instance("NODE_C", "v2.0", "seal_Y") 
    
    cand = get_candidate(entity, claim)
    print(f"[*] Provenance Trail size: {len(cand['provenance_trail'])}")
    
    # 4. Verification in Logic
    # I'll check the ledger for the effective_lineage_weight of the promotion if I can trigger it.
    print("\n--- Step 4: Promotion & Entropy Verification ---")
    # For Step 1-3, weight should be: 1.0 (A) + 0.2 (B, same attest) + 1.0 (C, diverse seal) = 2.2
    
    # Run cycles to promote
    for i in range(5):
        run_engine_instance("NODE_A", "v1.9.1", "seal_X")
    
    # Check ledger for promotion weight
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, "r") as f:
            lines = f.readlines()
            for line in reversed(lines):
                if "EXTERNAL_CANDIDATE_PROMOTION" in line and entity in line:
                    data = json.loads(line).get("data", {})
                    weight = data.get("effective_lineage_weight", 0.0)
                    print(f"[*] PROMOTION DETECTED. Effective Lineage Weight: {weight}")
                    if weight == 2.2:
                        print("SUCCESS: Entropy Weight correctly calculated (A:1.0, B:0.2, C:1.0).")
                    else:
                        print(f"ERROR: Unexpected weight {weight}. Expected 2.2.")
                    break
    
    print("\n[*] Simulation Complete.")

if __name__ == "__main__":
    test_attested_diversity()
