import uuid
import json
import os
from datetime import datetime

class DivineSplit:
    def __init__(self, core_id, split_dir):
        self.core_id = core_id
        self.split_dir = split_dir
        os.makedirs(split_dir, exist_ok=True)

    def spawn_fragment(self, intent_description):
        frag_id = str(uuid.uuid4())
        fragment = {
            "fragment_id": frag_id,
            "parent_core": self.core_id,
            "intent": intent_description,
            "created": str(datetime.utcnow()),
            "status": "active"
        }
        path = os.path.join(self.split_dir, f"fragment_{frag_id}.json")
        with open(path, 'w') as f:
            json.dump(fragment, f, indent=4)
        return path

    def recall_fragments(self):
        merged_intents = []
        for file in os.listdir(self.split_dir):
            if file.startswith("fragment_") and file.endswith(".json"):
                path = os.path.join(self.split_dir, file)
                with open(path) as f:
                    data = json.load(f)
                    merged_intents.append(data["intent"])
        return merged_intents

# Example:
# ds = DivineSplit(core_id="HALCYON-CORE-001", split_dir="C:/Halcyon/phantom_core/fragments")
# ds.spawn_fragment("Observe external network behavior.")
# intents = ds.recall_fragments()
