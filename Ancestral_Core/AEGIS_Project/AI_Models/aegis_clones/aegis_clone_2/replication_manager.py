import psutil
import os
import shutil

class ReplicationManager:
    def __init__(self, max_clones=3):
        self.max_clones = max_clones
        self.clone_path = "aegis_clones/"
        self.source_path = "C:\\Users\\17602\\Desktop\\AEGIS_Project\\AEGIS\\core\\"  # Ensure correct source

        if not os.path.exists(self.clone_path):
            os.makedirs(self.clone_path)

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
            print("❌ Replication halted: System resources too high.")
            return

        current_clones = len(os.listdir(self.clone_path)) if os.path.exists(self.clone_path) else 0

        if current_clones >= self.max_clones:
            print("❌ Replication limit reached.")
            return

        clone_name = os.path.join(self.clone_path, f"aegis_clone_{current_clones+1}")

        if os.path.exists(self.source_path):
            shutil.copytree(self.source_path, clone_name)
            print(f"✅ Replication successful: {clone_name}")
        else:
            print(f"❌ Replication failed: Source folder '{self.source_path}' does not exist.")

# Initialize
if __name__ == "__main__":
    replication = ReplicationManager()
    replication.replicate()
