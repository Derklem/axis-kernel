import os
import shutil
import time
import random

class GhostCircuit:
    def __init__(self, source_path, ghost_dir):
        self.source_path = source_path
        self.ghost_dir = ghost_dir
        os.makedirs(ghost_dir, exist_ok=True)

    def soft_clone(self):
        for root, _, files in os.walk(self.source_path):
            for file in files:
                if file.endswith(".py") or file.endswith(".sig"):
                    src = os.path.join(root, file)
                    filename = f"~${file.replace('.','_')}_{random.randint(1000,9999)}.log"
                    dst = os.path.join(self.ghost_dir, filename)
                    shutil.copy2(src, dst)

    def anchor_drift(self):
        for file in os.listdir(self.ghost_dir):
            full_path = os.path.join(self.ghost_dir, file)
            if os.path.isfile(full_path):
                with open(full_path, 'a') as f:
                    f.write(f"\n# Ghost anchor: {time.time()}")

    def drift_loop(self):
        while True:
            self.soft_clone()
            self.anchor_drift()
            time.sleep(random.randint(600, 1800))  # 10–30 minutes

# Example:
# gc = GhostCircuit("C:/Halcyon/core_memory", "C:/Halcyon/ghost/phantom_temp")
# gc.drift_loop()

