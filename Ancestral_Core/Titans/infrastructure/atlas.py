# atlas.py
import os

class Atlas:
    def __init__(self, base_path):
        self.base_path = base_path

    def map_directory(self):
        structure = {}
        for root, dirs, files in os.walk(self.base_path):
            structure[root] = {"dirs": dirs, "files": files}
        return structure
