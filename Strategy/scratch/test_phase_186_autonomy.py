import os
import json
import time
import random
from datetime import datetime, timezone
import subprocess

# Paths
STRATEGY_DIR = r"d:\Infinite\Infinity\Strategy"
MODEL_PATH = os.path.join(STRATEGY_DIR, "State", "ai_ecosystem_model.json")
OBS_DIR = r"D:\Infinite\Infinity\Inquiry"
SCRATCH_DIR = os.path.join(STRATEGY_DIR, "scratch")

def run_cycle():
    cmd = ["python", os.path.join(STRATEGY_DIR, "strategy_engine.py")]
    # Don't capture output so it streams to the main log
    result = subprocess.run(cmd)
    return result

def inject_random_observation(cycle):
    # Phase 186: Randomized domain-stratified intake
    domains = ["general", "safety_claim", "benchmark_claim", "rumor_claim", "leak_claim"]
    domain = random.choice(domains)
    
    entities = ["Llama-4-70B", "OpenAI_Strawberry", "Claude-35-Sonnet", "Anthropic", "Mistral", "DeepSeek-V3"]
    entity = random.choice(entities)
    
    sources = ["Safety_Watchdog", "Benchmark_Harvester", "Rumor_Mill", "Ecological_Observer", "Internal_Audit"]
    source = random.choice(sources)
    
    obs = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "entity": entity,
        "claim": f"Randomized signal for {entity} in cycle {cycle}.",
        "source_id": source,
        "source_type": "automated_sensor",
        "claim_domain": domain,
        "confidence": round(random.uniform(0.3, 0.9), 2)
    }
    
    filename = f"obs_random_{cycle}_{int(time.time())}.observation"
    with open(os.path.join(OBS_DIR, filename), "w") as f:
        json.dump(obs, f, indent=4)

def run_autonomy_gauntlet(target_cycles=2000):
    print(f"[*] Starting Phase 186 Autonomy Gauntlet ({target_cycles} cycles)...")
    
    for i in range(target_cycles):
        if i % 10 == 0:
            inject_random_observation(i)
            
        res = run_cycle()
        
        if res.returncode != 0:
            print(f"[-] CRITICAL FAILURE at Cycle {i}:")
            print(res.stderr)
            break
            
        if i % 100 == 0:
            print(f"[-] Cycle {i} complete. Forensic alignment nominal.")
            # Run dashboard export
            subprocess.run(["python", os.path.join(SCRATCH_DIR, "export_ecosystem_dashboard.py")])

    print("[*] Gauntlet Complete.")

if __name__ == "__main__":
    # Ensure a clean start if needed (optional, depends on use case)
    # subprocess.run(["python", os.path.join(SCRATCH_DIR, "super_clean.py")])
    run_autonomy_gauntlet()
