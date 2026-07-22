import json
from pathlib import Path

# === PATHS ===
base_path = Path("C:/Users/17602/Desktop/Living_Sandbox/Living_Sandbox/halcyon_root")
now_path = base_path / "Now.json"
echoes_path = base_path / "Construct_Echoes"

# === SELECT ECHO FILE TO MERGE ===
target_echo_id = "Echo_0002"  # <-- CHANGE THIS to merge a different Echo
target_echo_file = echoes_path / f"{target_echo_id}.json"

# === LOAD FILES ===
with open(now_path, 'r') as f:
    now_data = json.load(f)

with open(target_echo_file, 'r') as f:
    echo_data = json.load(f)

# === MERGE TRAITS ===
now_data["current_state"] = f"merged_from_{target_echo_id}"
now_data["last_updated"] = echo_data.get("timestamp", now_data["last_updated"])
now_data["origin"] = target_echo_id
now_data["traits"] = echo_data.get("traits", {})

# === MEMORY ENTRY ===
now_data.setdefault("memory", []).append({
    "timestamp": echo_data.get("timestamp"),
    "event": "merge_echo",
    "echo_id": target_echo_id,
    "notes": echo_data.get("notes", "No notes provided.")
})

# === SAVE ===
with open(now_path, 'w') as f:
    json.dump(now_data, f, indent=2)

print(f"{target_echo_id} merged into Now.json successfully.")
