import os
import time
from datetime import datetime

# === SETTINGS ===
DRIVES = ["C:\\", "D:\\", "E:\\"]  # Drives to scan
OUTPUT_DIR = "C:\\temp"           # Where to save the report
HOURS_BACK = 48                   # Look this many hours back

# === PREP ===
os.makedirs(OUTPUT_DIR, exist_ok=True)
cutoff = time.time() - (HOURS_BACK * 3600)
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
report_path = os.path.join(OUTPUT_DIR, f"SCAN_REPORT_{timestamp}.txt")

results = []

# === SCAN ===
def scan_path(base_path):
    for root, _, files in os.walk(base_path):
        for name in files:
            full_path = os.path.join(root, name)
            try:
                stat = os.stat(full_path)
                if stat.st_mtime >= cutoff or stat.st_ctime >= cutoff:
                    results.append({
                        "modified": stat.st_mtime,
                        "created": stat.st_ctime,
                        "size": stat.st_size,
                        "path": full_path
                    })
            except Exception:
                continue

for d in DRIVES:
    print(f"Scanning {d} ...")
    if os.path.exists(d):
        scan_path(d)

# === SORT & OUTPUT ===
results.sort(key=lambda x: x["modified"], reverse=True)

with open(report_path, "w", encoding="utf-8") as out:
    out.write(f"SCAN REPORT - Last {HOURS_BACK} Hours\n")
    out.write(f"Generated at {datetime.now()}\n")
    out.write("="*70 + "\n\n")
    for r in results:
        out.write(f"{datetime.fromtimestamp(r['modified'])} | "
                  f"{datetime.fromtimestamp(r['created'])} | "
                  f"{r['size']} bytes | {r['path']}\n")

print(f"\nScan complete. Report saved to {report_path}")
