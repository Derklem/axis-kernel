import os
import json
from datetime import datetime, timezone

MIND_DIR = r"D:\Mind"
PENDING_DIR = os.path.join(MIND_DIR, "Predictions", "pending")
REVISION_DIR = os.path.join(MIND_DIR, "Predictions", "needs_revision")

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def revise_design(file_path: str) -> None:
    design = load_json(file_path)
    
    preflight_result = design.get("preflight_result", {})
    revision_required = preflight_result.get("revision_required", "")
    
    if not revision_required:
        print(f"Skipping {os.path.basename(file_path)}: No revision_required field found.")
        return

    # Deterministic rewrite for Attention Budget
    if "Requested runs" in revision_required and "exceeds MAX_RUNS" in revision_required:
        # Check if independent variable is delta_clamp_enabled as expected by our deterministic block
        iv = design.get("independent_variable", "")
        
        # Apply the deterministic correction
        design["experimental_procedure"] = [
            f"Run 10 paired trials with {iv} set to true and false across matched parameter ranges.",
            "Record Delta Invariant validation failures for each paired trial.",
            "Compare failure rates between clamp-enabled and clamp-disabled conditions."
        ]
        
        revision_entry = {
            "revised_utc": datetime.now(timezone.utc).isoformat(),
            "source_status": "needs_revision",
            "reason": revision_required,
            "changed_fields": ["experimental_procedure"],
            "revision_rule": "reduce_requested_runs_to_MAX_RUNS"
        }
        
        # Initialize revision_history if missing
        if "revision_history" not in design:
            design["revision_history"] = []
            
        design["revision_history"].append(revision_entry)
        
        # Reset for preflight
        design["status"] = "pending"
        del design["preflight_result"]
        
        filename = os.path.basename(file_path)
        pending_path = os.path.join(PENDING_DIR, filename)
        
        save_json(pending_path, design)
        os.remove(file_path)
        print(f"Revision complete: {filename} moved back to pending.")
    else:
        print(f"Skipping {os.path.basename(file_path)}: No deterministic revision rule matches the reason '{revision_required}'.")

if __name__ == "__main__":
    if not os.path.exists(REVISION_DIR):
        print("No needs_revision directory found.")
        exit(0)
        
    for filename in os.listdir(REVISION_DIR):
        if filename.endswith(".json"):
            revise_design(os.path.join(REVISION_DIR, filename))
