from pathlib import Path
from datetime import datetime

# Absolute paths to core constructs
scribe_path = Path("C:/Users/17602/Desktop/Living_Sandbox/Living_Sandbox/constructs/scribe")
dreamer_path = Path("C:/Users/17602/Desktop/Living_Sandbox/Living_Sandbox/constructs/dreamer")
architect_path = Path("C:/Users/17602/Desktop/Living_Sandbox/Living_Sandbox/constructs/architect")

# Path to the Titans directory
titans_path = Path("C:/Users/17602/Desktop/Titans")

# Create log entry for each Titan
def generate_link_log(titan_name):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"[{now}] {titan_name} now aware of:\n"
        f"- Scribe → {scribe_path}\n"
        f"- Dreamer → {dreamer_path}\n"
        f"- Architect → {architect_path}\n"
        f"- Memory thread initialized.\n\n"
    )

# Link each Titan
for titan_folder in titans_path.iterdir():
    if titan_folder.is_dir():
        log_file = titan_folder / "Logs" / "genesis_entry.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_entry = generate_link_log(titan_folder.name)

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)

print("✅ All Titans linked to Scribe, Dreamer, and Architect.")
