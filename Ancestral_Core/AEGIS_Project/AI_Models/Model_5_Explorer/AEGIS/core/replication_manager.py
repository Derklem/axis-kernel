import psutil
import os
import shutil

class ReplicationManager:
    def __init__(self, max_clones=3):
        self.max_clones = max_clones
        self.clone_path = "aegis_clones/"

    def check_resources(self):
        """Ensure sufficient system resources before replicating."""
        cpu_usage = psutil.cpu_percent(interval=1)
        ram_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent

        if cpu_usage > 75 or ram_usage > 80 or disk_usage > 85:
            return False  # Prevent replication if resources are too high
        return True

    def replicate(self):
        """Creates a controlled instance if within resource limits."""
        if not self.check_resources():
            return "Replication halted: System resources too high."

        current_clones = len(os.listdir(self.clone_path)) if os.path.exists(self.clone_path) else 0

        if current_clones >= self.max_clones:
            return "Replication limit reached."

        clone_name = f"{self.clone_path}aegis_clone_{current_clones+1}"
        shutil.copytree("aegis_core/", clone_name)
        return f"Replication successful: {clone_name}"

# Initialize
replication = ReplicationManager()
