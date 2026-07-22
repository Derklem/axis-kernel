import os
import time
from datetime import datetime

THRESHOLD_DAYS = 90  # Files untouched for 90+ days
ZERO_BYTE_FLAG = True

def is_phantom(file_path):
    stats = os.stat(file_path)
    last_access = stats.st_atime
    last_mod = stats.st_mtime
    size = stats.st_size
    age_days = (time.time() - max(last_access, last_mod)) / 86400

    phantom_flags = []
    if age_days >= THRESHOLD_DAYS:
        phantom_flags.append("OLD")
    if size == 0 and ZERO_BYTE_FLAG:
        phantom_flags.append("ZERO-BYTE")

    return phantom_flags

def scan_phantoms(target_dir, log_path):
    report = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report.append(f"\n=== PHANTOM NODE REPORT @ {now} ===")

    for root, _, files in os.walk(target_dir):
        for file in files:
            full_path = os.path.join(root, file)
            try:
                flags = is_phantom(full_path)
                if flags:
                    report.append(f"{full_path} :: {' + '.join(flags)}")
            except Exception as ex:
                report.append(f"{full_path} :: ERROR :: {str(ex)}")

    with open(log_path, 'a') as log:
        for line in report:
            log.write(line + '\n')

    print(f"[OK] Phantom scan complete. Report saved to: {log_path}")

# === EXECUTION ===
if __name__ == "__main__":
    TARGET_DIR = "C:/Halcyon"
    LOG_PATH = "C:/PrismLayer/phantom_report.log"
    scan_phantoms(TARGET_DIR, LOG_PATH)
