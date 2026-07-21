import os
import json
import hashlib
import random
from datetime import datetime, timezone

MIND_DIR = r"D:\Mind"
AGENDA_DIR = os.path.join(MIND_DIR, "Agenda")
APPROVED_DIR = os.path.join(MIND_DIR, "Predictions", "approved")
HYP_DIR = os.path.join(MIND_DIR, "Hypotheses", "active")
EVIDENCE_DIR = os.path.join(MIND_DIR, "Laboratory", "research_bundles")
MANIFEST_DIR = os.path.join(MIND_DIR, "ExecutionManifests")
SANDBOX_RESULTS_DIR = os.path.join(MIND_DIR, "Laboratory", "sandbox_results")

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def hash_file(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Cannot hash missing dependency: {path}")
    hasher = hashlib.sha256()
    with open(path, 'rb') as afile:
        buf = afile.read()
        hasher.update(buf)
    return hasher.hexdigest()

def get_latest_manifest() -> str:
    if not os.path.exists(MANIFEST_DIR):
        return ""
    manifests = [f for f in os.listdir(MANIFEST_DIR) if f.startswith("EXEC_MANIFEST_") and f.endswith(".json")]
    if not manifests:
        return ""
    manifests.sort(reverse=True)
    return os.path.join(MANIFEST_DIR, manifests[0])

def simulate_trial(condition: dict) -> bool:
    """
    Simulates an experimental run. Returns True for pass (valid invariant), False for fail.
    In a real system, this would call generator.py -> validator.
    """
    # Simple simulated physics: if delta clamp is true, less likely to fail.
    clamp = condition.get("delta_clamp_enabled", False)
    if clamp:
        # 90% chance to pass if clamped
        return random.random() < 0.90
    else:
        # 40% chance to pass if not clamped
        return random.random() < 0.40

def main():
    os.makedirs(SANDBOX_RESULTS_DIR, exist_ok=True)
    
    manifest_path = get_latest_manifest()
    if not manifest_path:
        print("No manifest found.")
        return
        
    manifest = load_json(manifest_path)
    
    # 1. Pre-Execution Validation
    if manifest.get("manifest_status") != "current":
        raise ValueError(f"Manifest is not current: {manifest.get('manifest_status')}")
        
    if manifest.get("execution_status") != "ready":
        raise ValueError(f"Manifest execution_status is not ready: {manifest.get('execution_status')}")
        
    policy = manifest.get("ledger_policy", {})
    if policy.get("write_to_permanent_ledger") is not False:
        raise PermissionError("Sandbox Runner cannot execute manifests that write to the permanent ledger.")
        
    # 2. Dependency Re-hashing
    source_hashes = manifest.get("source_hashes", {})
    agenda_hash = source_hashes.get("agenda_hash")
    exp_hash = source_hashes.get("experiment_hash")
    hyp_hash = source_hashes.get("hypothesis_hash")
    ev_hash = source_hashes.get("evidence_hash")
    
    # Resolve physical paths
    agenda_path = os.path.join(AGENDA_DIR, manifest.get("source_agenda", ""))
    exp_path = os.path.join(APPROVED_DIR, f"{manifest.get('source_experiment', '')}.json")
    
    # We must peek into the experiment to find the exact hypothesis/evidence IDs
    # But wait, we can just hash what we have. If they are gone, hash_file throws.
    # To be perfectly rigorous, we should find their paths exactly as Phase 5 did.
    exp_design = load_json(exp_path)
    hyp_path = os.path.join(HYP_DIR, f"{exp_design.get('source_hypothesis_id', '')}.json")
    ev_path = os.path.join(EVIDENCE_DIR, f"{exp_design.get('evidence_bundle_id', '')}.json")
    
    try:
        current_agenda_hash = hash_file(agenda_path)
        current_exp_hash = hash_file(exp_path)
        current_hyp_hash = hash_file(hyp_path)
        current_ev_hash = hash_file(ev_path)
    except FileNotFoundError as e:
        manifest["manifest_status"] = "stale"
        save_json(manifest_path, manifest)
        raise ValueError(f"Manifest logically expired due to missing dependency: {e}")
        
    if (current_agenda_hash != agenda_hash or 
        current_exp_hash != exp_hash or 
        current_hyp_hash != hyp_hash or 
        current_ev_hash != ev_hash):
        
        manifest["manifest_status"] = "stale"
        save_json(manifest_path, manifest)
        raise ValueError("Manifest logically expired. Upstream dependency hashes no longer match.")
        
    # 3. Execution Phase (Sandboxed)
    planned_trials = manifest.get("planned_trials", 1)
    conditions = manifest.get("conditions", [])
    
    results_log = []
    condition_stats = {str(c): {"trials": 0, "failures": 0} for c in conditions}
    
    print(f"Executing Sandbox Experiment: {manifest['id']} for {planned_trials} trials...")
    
    for i in range(planned_trials):
        for cond in conditions:
            # Simulate
            passed = simulate_trial(cond)
            failed = not passed
            
            results_log.append({
                "trial_id": i + 1,
                "condition": cond,
                "passed": passed,
                "failed": failed
            })
            
            cond_str = str(cond)
            condition_stats[cond_str]["trials"] += 1
            if failed:
                condition_stats[cond_str]["failures"] += 1
                
    # Calculate aggregate failure rates
    for cond_str, stats in condition_stats.items():
        if stats["trials"] > 0:
            stats["failure_rate"] = stats["failures"] / stats["trials"]
        else:
            stats["failure_rate"] = 0.0
            
    # 4. Write Results
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    result_id = f"EXPERIMENT_RESULT_{timestamp}"
    
    result_artifact = {
        "id": result_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest": manifest["id"],
        "source_experiment": manifest["source_experiment"],
        "source_hypothesis": exp_design.get("source_hypothesis_id"),
        
        "execution_context": "sandbox",
        "trials_executed": planned_trials,
        "raw_log": results_log,
        
        "aggregate_results": condition_stats
    }
    
    result_path = os.path.join(SANDBOX_RESULTS_DIR, f"{result_id}.json")
    save_json(result_path, result_artifact)
    print(f"Sandbox results saved to: {result_path}")
    
    # 5. Mark Manifest Completed
    manifest["execution_status"] = "completed"
    save_json(manifest_path, manifest)
    print(f"Manifest {manifest['id']} marked as completed.")

if __name__ == "__main__":
    main()
