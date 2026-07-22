import os
import shutil

class ReplicationManager:
    def __init__(self):
        """Initialize the replication manager and ensure the clone directory exists."""
        self.clone_dir = "aegis_clones"
        os.makedirs(self.clone_dir, exist_ok=True)

    def get_next_clone_name(self):
        """Finds the next available clone number by checking existing clones."""
        existing_clones = [
            d for d in os.listdir(self.clone_dir) if d.startswith("aegis_clone_")
        ]
        next_number = len(existing_clones) + 1
        return f"aegis_clone_{next_number}"

    def replicate(self):
        """Creates a new clone with a unique name and avoids infinite nesting."""
        new_clone = os.path.join(self.clone_dir, self.get_next_clone_name())

        try:
            # Copy all files except logs and __pycache__
            shutil.copytree(
                os.path.dirname(__file__),
                new_clone,
                ignore=shutil.ignore_patterns("*.log", "__pycache__"),
            )

            print(f"📜 Genesis Document copied to {new_clone}")
            print(f"✅ Replication successful: {new_clone}")

        except Exception as e:
            print(f"❌ Replication failed: {e}")

if __name__ == "__main__":
    print("🛠️ Running Replication Test...")
    replicator = ReplicationManager()
    replicator.replicate()
