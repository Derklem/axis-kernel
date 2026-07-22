import datetime

class AlertSystem:
    def __init__(self):
        print("[AlertSystem] Initialized.")

    def send_alert(self, message, alert_level="INFO"):
        timestamp = datetime.datetime.now().isoformat()
        alert = f"[{timestamp}] [{alert_level}] {message}"
        print(alert)
        # Extendable: integrate with email, SMS, push notifications, etc.
