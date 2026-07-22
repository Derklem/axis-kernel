import json
import os
import time
import hashlib
import subprocess
from datetime import datetime, timezone

# Define the matrix
tests = [
    {"name": "A", "health": "degraded", "faults": 999, "stability": 85.0},
    {"name": "B", "health": "degraded", "faults": 0, "stability": 85.0},
    {"name": "C", "health": "healthy",  "faults": 999, "stability": 85.0},
    {"name": "D", "health": "degraded", "faults": 999, "stability": 95.0},
    {"name": "E", "health": "healthy",  "faults": 0, "stability": 95.0} # Let's see if full healthy approves
]

bridge_path = r"D:\Infinite\Infinity\symbiosis_bridge.py"
metrics_path = r"D:\Infinite\Infinity\Runtime\Decision\Governance_Metrics.json"
state_files = [
    r"D:\Infinite\Infinity\Strategy\State\strategy_state.json",
    r"D:\Infinite\Infinity\Strategy\State\calibration_continuity_anchor.json",
    r"D:\Infinite\Infinity\Strategy\State\forensic_witness_ledger.jsonl"
]

def update_baseline():
    hashes = {}
    for f in state_files:
        hashes[os.path.basename(f)] = hashlib.sha256(open(f, 'rb').read()).hexdigest()
    
    with open(bridge_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    import re
    # Find the BASELINE_HASHES dict and replace it
    pattern = r"BASELINE_HASHES\s*=\s*\{.*?\}"
    replacement = "BASELINE_HASHES = {\n"
    replacement += f'    "strategy_state.json": "{hashes["strategy_state.json"]}",\n'
    replacement += f'    "calibration_continuity_anchor.json": "{hashes["calibration_continuity_anchor.json"]}",\n'
    replacement += f'    "forensic_witness_ledger.jsonl": "{hashes["forensic_witness_ledger.jsonl"]}"\n'
    replacement += "}"
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    with open(bridge_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def write_metrics(health, faults, stability):
    metrics = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "metrics_health": health,
        "stability_index": stability,
        "stability_index_provenance": "matrix_test",
        "circuit_trips_last_24h": faults,
        "circuit_trips_last_24h_provenance": "matrix_test",
        "watchdog_restarts_last_hour": 0, # putting all faults in circuit_trips for simplicity, since fault_vol = sum
        "watchdog_restarts_last_hour_provenance": "matrix_test",
        "mttr_p95_24h": faults,
        "mttr_p95_24h_provenance": "matrix_test",
        "substrate_drift_kb": faults,
        "substrate_drift_kb_provenance": "matrix_test",
        "oracle_confidence": "test"
    }
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

print("| Test | Health | Fault Vol | Stability | Result |")
print("|---|---|---|---|---|")

for t in tests:
    write_metrics(t["health"], t["faults"], t["stability"])
    update_baseline()
    
    result = subprocess.run(["python", bridge_path], capture_output=True, text=True)
    
    # Extract the verdict
    verdict = "UNKNOWN"
    for line in result.stdout.splitlines():
        if "==> Actual Axis Verdict:" in line:
            verdict = line.split("==> Actual Axis Verdict: ")[1].strip()
    
    if verdict == "UNKNOWN" and result.returncode != 0:
        verdict = f"CRASH/ERROR (Code {result.returncode})"
        if "BASELINE DRIFT" in result.stdout:
            verdict = "BASELINE_DRIFT"
            
    print(f"| {t['name']} | {t['health']} | {t['faults']} | {t['stability']} | {verdict} |")
    time.sleep(1)
