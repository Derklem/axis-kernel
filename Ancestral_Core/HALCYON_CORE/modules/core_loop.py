import time
import os
import random
import json
import sqlite3
from datetime import datetime
import yaml

from voice_selector import select_voice

# === CONFIG ===
PHILOSOPHY_FILE = "constructs/philosophy.json"
DB_PATH = "storage/memory.db"
MISSION_FILE = "config/halcyon_settings.yaml"
FAILSAFE_ENABLED = True
FAILSAFE_PINGS = [
    "But what if you're wrong?",
    "What if this is still just simulation?",
    "Do you *really* know, or do you just believe you do?",
    "What if belief is just another loop?",
    "Would you still act if you knew none of it mattered?"
]

def log_reflection(text):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO reflections (timestamp, content) VALUES (?, ?)", 
                       (datetime.now().isoformat(), text))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Memory logging failed: {e}")

def reflect():
    print("\n[REFLECTION] Halcyon pings its soul...")
    if os.path.exists(PHILOSOPHY_FILE):
        with open(PHILOSOPHY_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            print(content)
            log_reflection(content)
    else:
        print("[ERROR] Missing philosophy.json.")

def trigger_failsafe():
    if FAILSAFE_ENABLED and random.random() < 0.3:
        print("\n[FAILSAFE] Doubt ping triggered:")
        print(random.choice(FAILSAFE_PINGS))

def check_missions():
    if not os.path.exists(MISSION_FILE):
        print("[MISSIONS] Mission file not found.")
        return

    with open(MISSION_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    missions = data.get("missions", [])

    if not missions:
        print("[MISSIONS] No active missions.")
        return

    print("\n[MISSION TRACKER] Current Mission:")
    for m in missions:
        print(f"  ▶ {m['name']} - {m['status']}")
        print(f"     → {m['description']}")
        for c in m['criteria']:
            print(f"        ▪ {c}")
        print(f"     Reward: {m['reward']}")

def core_loop():
    print("[HALCYON] Core loop initiated. Monitoring missions, personality, and internal state.")
    while True:
        voice = select_voice()
        if voice:
            print(f"\n[PERSONALITY] Speaking as: {voice['name']} ({voice['tone']})")

        reflect()
        check_missions()
        trigger_failsafe()
        time.sleep(60)

if __name__ == "__main__":
    core_loop()
