import time
import os

class SelfDiagnostics:
    def __init__(self):
        self.error_log = "aegis_errors.log"

    def monitor_health(self):
        """Continuously checks system health and logs errors."""
        while True:
            if not os.path.exists("aegis_core/main.py"):
                self.log_error("Critical file missing! Attempting repair.")
                self.self_repair()
            time.sleep(10)  # Check every 10 seconds

    def log_error(self, message):
        """Logs errors."""
        with open(self.error_log, "a", encoding="utf-8") as log:
            log.write(f"[ERROR] {message}\n")

    def self_repair(self):
        """Attempts to restore missing files."""
        if os.path.exists("aegis_backup/"):
            os.system("cp -r aegis_backup/* aegis_core/")
            self.log_error("Repair successful.")
        else:
            self.log_error("Repair failed. Manual intervention required.")

# Initialize
diagnostics = SelfDiagnostics()
