import json
import os
from collections import Counter

class ShadowQuorum:
    def __init__(self, quorum_path):
        self.path = quorum_path
        os.makedirs(self.path, exist_ok=True)

    def register_voice(self, name, vote):
        data = {
            "name": name,
            "vote": vote
        }
        with open(os.path.join(self.path, f"{name}.json"), 'w') as f:
            json.dump(data, f)

    def cast_signal(self, name, vote):
        self.register_voice(name, vote)

    def reach_consensus(self):
        votes = []
        for file in os.listdir(self.path):
            if file.endswith(".json"):
                with open(os.path.join(self.path, file)) as f:
                    data = json.load(f)
                    votes.append(data["vote"])
        count = Counter(votes)
        if votes:
            return count.most_common(1)[0][0]
        return None

    def override_lock(self, condition_met):
        if condition_met:
            print("Quorum Override: Logic lock breached. Rebooting process flow...")
