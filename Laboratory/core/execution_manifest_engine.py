import os
import json
import hashlib
from datetime import datetime, timezone

MIND_DIR = r"D:\Mind"
AGENDA_DIR = os.path.join(MIND_DIR, "Agenda")
APPROVED_DIR = os.path.join(MIND_DIR, "Predictions", "approved")
HYP_DIR = os.path.join(MIND_DIR, "Hypotheses", "active")
EVIDENCE_DIR = os.path.join(MIND_DIR, "Laboratory", "research_bundles")
MANIFEST_DIR = os.path.join(MIND_DIR, "ExecutionManifests")

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def hash_file(path: str) -> str:
    """Returns SHA-256 hash of a file's contents."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Cannot hash missing dependency: {path}")
    hasher = hashlib.sha256()
    with open(path, 'rb') as afile:
        buf = afile.read()
        hasher.update(buf)
    return hasher.hexdigest()

def get_latest_agenda() -> str:
    if not os.path.exists(AGENDA_DIR):
        return ""
    agendas = [f for f in os.listdir(AGENDA_DIR) if f.startswith("AGENDA_") and f.endswith(".json")]
    if not agendas:
        return ""
    agendas.sort(reverse=True)
    return os.path.join(AGENDA_DIR, agendas[0])

def main():
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    
    agenda_path = get_latest_agenda()
    if not agenda_path:
        print("No agenda found. Exiting.")
        return
        
    agenda = load_json(agenda_path)
    agenda_filename = os.path.basename(agenda_path)
    exp_id = agenda.get("selected_experiment")
    
    if not exp_id:
        print("Agenda has no selected_experiment. Exiting.")
        return
        
    exp_filename = f"{exp_id}.json"
    exp_path = os.path.join(APPROVED_DIR, exp_filename)
    
    safety_checks = []
    
    if os.path.exists(agenda_path):
        safety_checks.append("agenda_source_exists")
    else:
        raise ValueError("Agenda source missing.")
        
    if os.path.exists(exp_path):
        safety_checks.append("experiment_source_exists")
    else:
        raise ValueError(f"Experiment source missing: {exp_path}")
        
    design = load_json(exp_path)
    
    if design.get("status") == "approved":
        safety_checks.append("experiment_status_approved")
    else:
        raise ValueError("Experiment status is not approved.")
        
    if design.get("fixture") is not True:
        safety_checks.append("fixture_false")
    else:
        raise ValueError("Cannot execute a fixture.")
        
    preflight = design.get("preflight_result", {})
    if "detected_requested_runs" not in preflight:
        raise ValueError("Missing detected_requested_runs in preflight_result.")
    planned_trials = preflight["detected_requested_runs"]
    
    if planned_trials <= 10:  # Assuming MAX_RUNS = 10 from Phase 3
        safety_checks.append("planned_trials_within_budget")
    else:
        raise ValueError(f"Trials ({planned_trials}) exceed budget.")
        
    # Get upstream paths for hashing
    hyp_id = design.get("source_hypothesis_id", "")
    hyp_path = os.path.join(HYP_DIR, f"{hyp_id}.json")
    
    ev_id = design.get("evidence_bundle_id", "")
    ev_path = os.path.join(EVIDENCE_DIR, f"{ev_id}.json")
    
    # Hash dependencies
    source_hashes = {
        "agenda_hash": hash_file(agenda_path),
        "experiment_hash": hash_file(exp_path),
        "hypothesis_hash": hash_file(hyp_path),
        "evidence_hash": hash_file(ev_path)
    }
    
    iv = design.get("independent_variable", "unknown")
    dv = design.get("dependent_variable", "unknown")
    
    manifest = {
        "id": f"EXEC_MANIFEST_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_status": "current",
        "execution_status": "ready",
        
        "source_agenda": agenda_filename,
        "source_experiment": exp_id,
        "source_hashes": source_hashes,
        
        "execution_environment": {
            "runner_version": "runner_v1",
            "generator_version": "generator_v1",
            "validator_version": "verifier_3.0.0",
            "python_version": "3.12",
            "required_hooks": [iv]
        },
        
        "planned_trials": planned_trials,
        "independent_variable": iv,
        "conditions": [
            {iv: True},
            {iv: False}
        ],
        "measurement_targets": [dv],
        
        "ledger_policy": {
            "write_to_permanent_ledger": False,
            "write_to_sandbox_results": True
        },
        
        "safety_checks": safety_checks
    }
    
    manifest_path = os.path.join(MANIFEST_DIR, f"{manifest['id']}.json")
    save_json(manifest_path, manifest)
    
    print(f"Execution Manifest generated successfully: {os.path.basename(manifest_path)}")
    print(f"Status: {manifest['manifest_status']}, Execution: {manifest['execution_status']}")

if __name__ == "__main__":
    main()
