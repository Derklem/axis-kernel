import os
import time
import hashlib

class SecurityManager:
    def __init__(self):
        self.core_files = ["aegis_core/main.py"]
        self.last_hashes = self.compute_hashes()

    def compute_hashes(self):
        """Generate file integrity hashes."""
        hashes = {}
        for file in self.core_files:
            if os.path.exists(file):
                with open(file, "rb") as f:
                    hashes[file] = hashlib.sha256(f.read()).hexdigest()
        return hashes

    def monitor_integrity(self):
        """Detects unauthorized file changes."""
        while True:
            for file in self.core_files:
                if os.path.exists(file):
                    with open(file, "rb") as f:
                        new_hash = hashlib.sha256(f.read()).hexdigest()
                        if new_hash != self.last_hashes[file]:
                            self.lock_files()
                            os.system("shutdown -r now")  # Auto-restart
            time.sleep(5)

    def lock_files(self):
        """Locks core files if tampered with."""
        os.system("chmod 000 aegis_core/main.py")
        print("Security lockdown activated.")

# Initialize
security = SecurityManager()
security.monitor_integrity()
