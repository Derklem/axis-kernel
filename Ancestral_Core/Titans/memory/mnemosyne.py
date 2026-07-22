# mnemosyne.py
class Mnemosyne:
    def __init__(self):
        self.archive = {}

    def store(self, key, data):
        self.archive[key] = data

    def recall(self, key):
        return self.archive.get(key, None)

    def all_keys(self):
        return list(self.archive.keys())
