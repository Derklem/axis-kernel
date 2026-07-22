import os
import json
import time
from datetime import datetime, timezone
import subprocess

# Paths
STRATEGY_DIR = r"d:\Infinite\Infinity\Strategy"
OBS_DIR = r"D:\Infinite\Infinity\Inquiry"
REGISTRY_PATH = r"d:\infinite\Warehouse\warehouse_structural_registry.json"

def inject_structural_claim():
    # Source 1
    obs1 = {
        "artifact_type": "ecosystem_observation",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "entity": "coordinated_executor.py",
        "claim": "coordinated_executor.py is redundant with the new sovereign_pulse architecture.",
        "source_id": "Structural_Auditor_A",
        "source_type": "internal_audit",
        "claim_domain": "general",
        "confidence": 0.95
    }
    # Source 2
    obs2 = {
        "artifact_type": "ecosystem_observation",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "entity": "coordinated_executor.py",
        "claim": "coordinated_executor.py is redundant with the new sovereign_pulse architecture.",
        "source_id": "Structural_Auditor_B",
        "source_type": "external_sensor", # Different type/family
        "claim_domain": "general",
        "confidence": 0.90
    }
    
    if not os.path.exists(OBS_DIR):
        os.makedirs(OBS_DIR)
    
    with open(os.path.join(OBS_DIR, f"obs_1_{int(time.time())}.observation"), "w") as f:
        json.dump(obs1, f, indent=4)
    with open(os.path.join(OBS_DIR, f"obs_2_{int(time.time())}.observation"), "w") as f:
        json.dump(obs2, f, indent=4)
    print(f"[*] Injected structural quorum for coordinated_executor.py")

def verify_actuation():
    if not os.path.exists(REGISTRY_PATH):
        print("ERROR: Registry not found.")
        return False
        
    with open(REGISTRY_PATH, "r") as f:
        registry = json.load(f)
        
    sig = registry.get("signatures", {}).get("coordinated_executor.py", {})
    if "METABOLIC_VERIFIED" in sig.get("tags", []):
        print("[+] SUCCESS: Structural actuation verified for coordinated_executor.py")
        return True
    else:
        print("[-] FAILURE: Structural actuation NOT detected.")
        return False

def run_test():
    # 1. Clean start
    subprocess.run(["python", os.path.join(STRATEGY_DIR, "scratch", "super_clean.py")])
    # 2. Index workspace
    subprocess.run(["python", r"d:\infinite\Warehouse\semantic_ontology_engine.py"])
    
    # 3. Inject claim
    inject_structural_claim()
    
    # 4. Run cycles until promotion (10 cycles for general domain)
    print("[*] Running 11 cycles to trigger promotion...")
    for i in range(11):
        subprocess.run(["python", os.path.join(STRATEGY_DIR, "strategy_engine.py")], capture_output=True)
        
    # 5. Verify
    verify_actuation()

if __name__ == "__main__":
    run_test()
