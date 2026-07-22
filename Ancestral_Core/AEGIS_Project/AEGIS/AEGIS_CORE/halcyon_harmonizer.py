
import json
import os
import datetime
from core.memory.harmonics.harmonic_reconciliation import HarmonicReconciler

def load_anchors(filepath):
    with open(filepath, "r") as f:
        data = json.load(f)
        return data.get("anchors", [])

def load_pulses(filepath):
    with open(filepath, "r") as f:
        data = json.load(f)
        return data.get("pulses", [])

def save_bridges(bridges, output_path):
    timestamp = datetime.datetime.utcnow().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "bridges": bridges
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            existing = json.load(f)
    else:
        existing = []
    existing.append(log_entry)
    with open(output_path, "w") as f:
        json.dump(existing, f, indent=2)
    print(f"[✓] Logged {len(bridges)} new bridges at {timestamp}")

def run_harmonizer():
    reconciler = HarmonicReconciler()

    anchor_path = "core/memory/harmonics/node_anchors.json"
    anchors = load_anchors(anchor_path)
    for anchor in anchors:
        reconciler.register_anchor(anchor["node_id"], anchor["content"], anchor["category"])

    # Assume in-memory pulses are still live; otherwise could load from file
    reconciler.reconcile_all()
    save_bridges(reconciler.bridges, "harmonic_log/halcyon_bridge_log.json")

if __name__ == "__main__":
    run_harmonizer()
