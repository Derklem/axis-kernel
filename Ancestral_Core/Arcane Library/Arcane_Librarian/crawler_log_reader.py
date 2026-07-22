import json
from pathlib import Path
from datetime import datetime

LOG_PATH = Path("E:/Arcane Library/Arcane_Librarian/crawler_activity_log.json")

def summarize_crawls():
    if not LOG_PATH.exists():
        print("❌ No crawler log found.")
        return

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]

    if not entries:
        print("📭 No entries in crawler log yet.")
        return

    print("\n📜 Crawler Activity Summary:\n")

    for entry in entries:
        timestamp = entry.get("timestamp", "unknown time")
        file = entry.get("file_saved", "unknown file")
        status = entry.get("status", "unknown status")
        print(f"[{timestamp}] ➔ {file} ({status})")

    print(f"\n✅ {len(entries)} total entries summarized.")

if __name__ == "__main__":
    summarize_crawls()
