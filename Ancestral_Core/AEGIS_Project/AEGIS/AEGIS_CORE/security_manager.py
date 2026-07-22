import os
import time
import hashlib

class SecurityManager:
    def __init__(self):
        print("🔒 Initializing Security Manager...")
        self.core_files = ["aegis_core/main.py"]
        self.last_hashes = self.compute_hashes()

    def compute_hashes(self):
        """Generate file integrity hashes."""
        print("🔍 Computing file integrity hashes...")
        hashes = {}
        for file in self.core_files:
            if os.path.exists(file):
                with open(file, "rb") as f:
                    hashes[file] = hashlib.sha256(f.read()).hexdigest()
        print("✅ Hashes computed successfully.")
        return hashes

    def monitor_integrity(self):
        """Detects unauthorized file changes."""
        print("🔍 Monitoring file integrity...")
        while True:
            for file in self.core_files:
                if os.path.exists(file):
                    with open(file, "rb") as f:
                        new_hash = hashlib.sha256(f.read()).hexdigest()
                        if new_hash != self.last_hashes[file]:
                            print("❌ FILE TAMPERING DETECTED!")
                            self.lock_files()
                            os.system("shutdown -r now")  # Auto-restart
            time.sleep(5)

    def lock_files(self):
        """Locks core files if tampered with."""
        print("🔒 Security lockdown activated.")
        os.system("chmod 000 aegis_core/main.py")

# Initialize
if __name__ == "__main__":
    try:
        security = SecurityManager()
        security.monitor_integrity()
    except Exception as e:
        print(f"❌ Security Manager Failed: {e}")
