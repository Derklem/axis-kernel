import json
from pathlib import Path
from datetime import datetime

# === PATHS ===
base_path = Path("C:/Users/17602/Desktop/Living_Sandbox/Living_Sandbox/halcyon_root")
launch_path = base_path / "launch_as_echo.json"
now_path = base_path / "Now.json"

# === LOAD LAUNCH PAYLOAD ===
with open(launch_path, 'r') as f:
    launch_data = json.load(f)

# === APPLY TO NOW ===
new_state = {
    "current_state": f"launched_from_{launch_data.get('launched_from', 'unknown')}",
    "last_updated": datetime.utcnow().isoformat() + "Z",
    "traits": launch_data.get("traits", {}),
    "origin": launch_data.get("launched_from"),
    "memory": [
        {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": "launched_as_echo",
            "echo_id": launch_data.get("launched_from"),
            "notes": launch_data.get("notes", "No notes.")
        }
    ]
}

# === SAVE NOW ===
with open(now_path, 'w') as f:
    json.dump(new_state, f, indent=2)

print(f"[LAUNCH] Halcyon launched as {launch_data.get('launched_from')}")
