
import os
from pathlib import Path
from datetime import datetime

MEMORY_DIR = Path(__file__).resolve().parent / "memory"

def remember(construct, user_input, response):
    MEMORY_DIR.mkdir(exist_ok=True)
    memory_file = MEMORY_DIR / f"{construct}.log"
    timestamp = datetime.utcnow().isoformat() + "Z"
    with open(memory_file, "a") as f:
        f.write(f"[{timestamp}] USER: {user_input}\n")
        f.write(f"[{timestamp}] {construct.upper()}: {response}\n\n")

def recall(construct, limit=5):
    memory_file = MEMORY_DIR / f"{construct}.log"
    if not memory_file.exists():
        return []
    with open(memory_file, "r") as f:
        lines = f.readlines()
    entries = [line.strip() for line in lines if line.strip()]
    return entries[-limit*2:]  # Return last N exchanges (user + construct)
