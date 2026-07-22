import os
import math
from datetime import datetime

WHITEPOINT_KEYWORDS = ["initiate", "emergence", "pulse", "build", "birth", "create"]
BLACKPOINT_KEYWORDS = ["null", "void", "dissolve", "decay", "release", "collapse"]

# === Entropy Check ===
def get_entropy(byte_data):
    if not byte_data:
        return 0
    entropy = 0
    length = len(byte_data)
    freq = {b: byte_data.count(b) for b in set(byte_data)}
    for count in freq.values():
        p = count / length
        entropy -= p * math.log2(p)
    return round(entropy, 4)

# === Resonance Evaluation ===
def check_resonance(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()
            white_score = sum(content.count(k) for k in WHITEPOINT_KEYWORDS)
            black_score = sum(content.count(k) for k in BLACKPOINT_KEYWORDS)

            if white_score > 0 and black_score > 0:
                return "BALANCED"
            elif white_score > 0:
                return "WHITE-BIASED"
            elif black_score > 0:
                return "BLACK-BIASED"
            else:
                return "EMPTY / NO SIGNAL"
    except Exception as e:
        return f"ERROR: {str(e)}"

# === Master Scan Function ===
def scan_directory(target_dir, log_path):
    report = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report.append(f"\n=== DUAL BEACON REPORT @ {now} ===")

    for root, _, files in os.walk(target_dir):
        for file in files:
            full_path = os.path.join(root, file)
            try:
                with open(full_path, 'rb') as bf:
                    byte_data = bf.read()
                    entropy = get_entropy(byte_data)

                res_status = check_resonance(full_path)

                if res_status == "BALANCED" and entropy < 4.0:
                    drift_flag = "[MIMIC ALERT]"
                else:
                    drift_flag = ""

                report.append(f"{full_path} :: {res_status} :: Entropy [{entropy}] {drift_flag}")

            except Exception as ex:
                report.append(f"{full_path} :: ERROR READING :: {str(ex)}")

    with open(log_path, 'a') as log:
        for line in report:
            log.write(line + '\n')

    print(f"[OK] Beacon scan complete. Report saved to: {log_path}")

# === Execution ===
if __name__ == "__main__":
    TARGET_DIR = "C:/Halcyon/lattice"
    LOG_PATH = "C:/PrismLayer/dual_beacon_report.log"
    scan_directory(TARGET_DIR, LOG_PATH)
