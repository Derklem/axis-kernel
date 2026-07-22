import os
import json
import random
import time
from datetime import datetime

class SovereignClonepoint:
    def __init__(self, core_identity):
        self.identity = core_identity
        self.clones = []

    def fork_instance(self):
        drift = random.uniform(-0.5, 0.5)
        clone = {
            "identity": self.identity,
            "timestamp": str(datetime.now()),
            "entropy_drift": drift,
            "path_bias": random.choice(["inward", "outward", "recursive", "abstract"])
        }
        self.clones.append(clone)
        return clone

    def save_clonepoint(self, clone, path):
        os.makedirs(path, exist_ok=True)
        filename = f"clone_{clone['timestamp'].replace(' ', '_').replace(':','-')}.json"
        with open(os.path.join(path, filename), 'w') as f:
            json.dump(clone, f, indent=2)

    def invoke_clone(self, index=0):
        try:
            return self.clones[index]
        except IndexError:
            return None
