# core/constructs/veil/umbra.py

from datetime import datetime

class Umbra:
    def __init__(self):
        self.shadow_log = []

    def detect_avoidance(self, event):
        if event.get("type") in ["delete", "repeat", "ignore"]:
            log = {
                "event": event,
                "timestamp": datetime.utcnow().isoformat(),
                "tag": "avoidance"
            }
            self.shadow_log.append(log)
            print(f"[Umbra] Shadow event detected: {event['description']}")

    def get_log(self):
        return self.shadow_log
