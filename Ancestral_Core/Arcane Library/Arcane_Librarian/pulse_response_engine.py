# pulse_response_engine.py
# Watches the sync pulse log and responds to anomalies

import os
import datetime

PULSE_LOG = "E:/Arcane Library/pulse_engine/sync_pulse_log.txt"
FAULT_LOG = "E:/Arcane Library/Arcane_Vault/pulse_faults.log"
VAULT_PATH = "E:/Arcane Library"
BACKUP_PATH = "F:/Arcane_Library_Backups/"  # You can adjust this if needed

FAST_THRESHOLD_SECONDS = 5
SLOW_THRESHOLD_SECONDS = 900  # 15 minutes


def read_last_pulses():
    if not os.path.exists(PULSE_LOG):
        return []
    with open(PULSE_LOG, "r", encoding="utf-8") as f:
        lines = f.readlines()
    timestamps = []
    for line in lines[-10:]:
        try:
            ts = line.split("sync at: ")[-1].split(" —")[0]
            timestamps.append(datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))
        except:
            continue
    return timestamps


def calculate_intervals(times):
    return [(t2 - t1).total_seconds() for t1, t2 in zip(times, times[1:])]


def lockdown_library():
    for root, dirs, files in os.walk(VAULT_PATH):
        for f in files:
            try:
                os.chmod(os.path.join(root, f), 0o444)
            except:
                continue


def trigger_backup():
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup_dir = os.path.join(BACKUP_PATH, f"pulse_redundancy_{now}")
    os.makedirs(backup_dir, exist_ok=True)
    for root, dirs, files in os.walk(VAULT_PATH):
        for file in files:
            try:
                src = os.path.join(root, file)
                dst = os.path.join(backup_dir, os.path.relpath(src, VAULT_PATH))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(src, "rb") as fsrc:
                    with open(dst, "wb") as fdst:
                        fdst.write(fsrc.read())
            except:
                continue


def issue_silent_alarm(reason):
    with open(FAULT_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] ⚠️ {reason}\n")


def pulse_monitor():
    times = read_last_pulses()
    if len(times) < 2:
        print("📡 Not enough pulse data yet.")
        return

    intervals = calculate_intervals(times)
    if not intervals:
        return

    avg_interval = sum(intervals) / len(intervals)

    if avg_interval < FAST_THRESHOLD_SECONDS:
        print("⚡ Rapid pulse detected. Locking down library.")
        lockdown_library()
        issue_silent_alarm("Rapid pulse storm detected. Library locked down.")

    elif avg_interval > SLOW_THRESHOLD_SECONDS:
        print("🌀 Slow pulse drift detected. Triggering backup redundancy.")
        trigger_backup()
        issue_silent_alarm("Pulse drift anomaly detected. Redundant backup triggered.")

    else:
        print("✅ Pulse rhythm stable.")


if __name__ == "__main__":
    pulse_monitor()
