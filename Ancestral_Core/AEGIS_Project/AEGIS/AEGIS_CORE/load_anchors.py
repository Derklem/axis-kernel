
import json
import os
from core.memory.harmonics.harmonic_reconciliation import HarmonicReconciler

def load_anchors_from_file(filepath):
    reconciler = HarmonicReconciler()
    if not os.path.exists(filepath):
        print(f"[ERROR] Anchor file not found: {filepath}")
        return

    with open(filepath, "r") as f:
        data = json.load(f)
        for anchor in data.get("anchors", []):
            reconciler.register_anchor(
                node_id=anchor["node_id"],
                content=anchor["content"],
                category=anchor["category"]
            )
        print(f"[✓] Loaded {len(data.get('anchors', []))} anchors into Reconciler.")

if __name__ == "__main__":
    anchor_file = "core/memory/harmonics/node_anchors.json"
    load_anchors_from_file(anchor_file)
