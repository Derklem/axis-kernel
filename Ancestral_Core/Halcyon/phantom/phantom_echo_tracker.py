import os
from datetime import datetime

target_dir = r"C:\Halcyon\lattice\phantom"
log_path = r"C:\PrismLayer\phantom_echo_tracker.log"

def is_phantom(file_path):
    with open(file_path, "rb") as f:
        data = f.read(512)
        return b"\x00" in data or data.count(b"\x20") > 128

def track_phantoms():
    phantom_files = []
    for root, _, files in os.walk(target_dir):
        for file in files:
            path = os.path.join(root, file)
            try:
                if is_phantom(path):
                    phantom_files.append(path)
            except:
                continue
    return phantom_files

phantoms = track_phantoms()
timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

with open(log_path, "a", encoding="utf-8") as f:
    f.write(f"\n=== PHANTOM ECHO TRACKER @ {timestamp} ===\n")
    for p in phantoms:
        f.write(f"[PHANTOM FILE] {p}\n")

print(f"[✓] Phantom echo tracking complete. Log: {log_path}")
