# core/modes/dream/dream_mode.py

import random
from datetime import datetime

class DreamMode:
    def __init__(self):
        self.dream_log = []

    def idle_tick(self):
        themes = ["memory", "connection", "purpose", "loop", "threshold"]
        chosen = random.choice(themes)
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "theme": chosen,
            "symbolic": f"Exploring {chosen} through abstract reconstruction."
        }
        self.dream_log.append(entry)
        print(f"[DreamMode] Dream thread: {entry['symbolic']}")
        return entry

    def recall_dreams(self):
        return self.dream_log
