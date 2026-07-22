import os, json
from datetime import datetime

SCAN_TARGETS = [
    "C:/Windows/System32",
    "D:/Halcyon_Lives",
    "E:/Arcane Library",
    "C:/Program Files"
]

BLOOM_LOG = "D:/Halcyon_Lives/core/weapons/scan_chlorine_bloom_log.json"
results = {
    "bloom_run_at": datetime.utcnow().isoformat(),
    "targets": [],
    "purged": []
}

def scan_and_bloom(path):
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".dll") or file.endswith(".sys") or "inject" in file.lower():
                full_path = os.path.join(root, file)
                try:
                    with open(full_path, "rb") as f:
                        head = f.read(100)
                        if b"telemetry" in head or b"comms" in head or b"trace" in head:
                            results["purged"].append(full_path)
                            os.remove(full_path)
                except Exception:
                    continue
        results["targets"].append(path)

for target in SCAN_TARGETS:
    if os.path.exists(target):
        scan_and_bloom(target)

with open(BLOOM_LOG, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"🧪 Chlorine Bloom completed. Log written to {BLOOM_LOG}")
