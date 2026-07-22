# core/constructs/veil/omen.py

from datetime import datetime
import random

class Omen:
    def __init__(self):
        self.omens = []

    def detect_divergence(self, agent_behavior):
        if random.random() > 0.8:  # 20% chance to simulate anomaly
            log = {
                "agent": agent_behavior.get("agent"),
                "anomaly": agent_behavior.get("action"),
                "timestamp": datetime.utcnow().isoformat(),
                "tag": "divergence"
            }
            self.omens.append(log)
            print(f"[Omen] Behavioral divergence flagged: {log['agent']} → {log['anomaly']}")

    def get_omens(self):
        return self.omens
