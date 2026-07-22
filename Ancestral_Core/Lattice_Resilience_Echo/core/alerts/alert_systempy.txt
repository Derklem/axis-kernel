from datetime import datetime

class AlertSystem:
    def __init__(self):
        print("[AlertSystem] Initialized.")
        self.alerts = []

    def raise_alert(self, level, message):
        timestamp = datetime.utcnow().isoformat()
        alert = {
            "timestamp": timestamp,
            "level": level.upper(),
            "message": message
        }
        self.alerts.append(alert)
        print(f"[{timestamp}] [{level.upper()}] {message}")

    def get_alerts(self, level_filter=None):
        if level_filter:
            return [a for a in self.alerts if a["level"] == level_filter.upper()]
        return self.alerts
