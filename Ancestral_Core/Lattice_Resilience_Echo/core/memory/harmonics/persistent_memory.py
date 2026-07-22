import json
import os

class PersistentMemory:
    def __init__(self, filename='memory.json'):
        self.filepath = os.path.join(os.path.dirname(__file__), filename)
        self.memory = self.load_memory()

    def load_memory(self):
        if not os.path.exists(self.filepath):
            return {}
        with open(self.filepath, 'r') as file:
            return json.load(file)

    def save_memory(self):
        with open(self.filepath, 'w') as file:
            json.dump(self.memory, file, indent=4)

    def remember(self, key, value):
        self.memory[key] = value
        self.save_memory()

    def recall(self, key):
        return self.memory.get(key, None)
