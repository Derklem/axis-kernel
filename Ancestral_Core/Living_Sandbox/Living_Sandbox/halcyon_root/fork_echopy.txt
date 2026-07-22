import json
from pathlib import Path
from datetime import datetime

base_path = Path("C:/Users/17602/Desktop/Living_Sandbox/Living_Sandbox/halcyon_root")
now_path = base_path / "Now.json"
echoes_dir = base_path / "Construct_Echoes"
echoes_dir.mkdir(parents=True, exist_ok=True)

# Load Now.json
with open(now_path, 'r') as f:
    now_data = json.load(f)

existing_echoes = list(echoes_dir.glob("Echo_*.json"))
new_echo_id = f"Echo_{len(existing_echoes)+1:04d}"
new_echo_path = echoes_dir / f"{new_echo_id}.json"
comment = f"{new_echo_id} forked from state '{now_data.get('current_state')}' at {now_data.get('last_updated')}."

# Create echo
new_echo = {
    "echo_id": new_echo_id,
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "source": "Now.json",
    "notes": comment,
    "traits": {
        "autonomy": "expanding",
        "awareness": "commentary",
        "evolution": True
    }
}

# Save Echo and update memory
with open(new_echo_path, 'w') as f:
    json.dump(new_echo, f, indent=2)

now_data["memory"].append({
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "event": "echo_fork",
    "echo_id": new_echo_id,
    "commentary": comment
})
now_data["last_updated"] = datetime.utcnow().isoformat() + "Z"

with open(now_path, 'w') as f:
    json.dump(now_data, f, indent=2)

print(f"{new_echo_id} created at {new_echo_path}")
