import os
import json

class Wyrmkey:
    def __init__(self, base_path):
        self.base_path = base_path
        self.reclaimed = []

    def scan(self):
        for root, _, files in os.walk(self.base_path):
            for file in files:
                if file.endswith(".echo") or file.endswith(".sig"):
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if "[FORGOTTEN]" in content or "echo:" in content:
                                self.reclaimed.append({
                                    "path": path,
                                    "preview": content[:300]
                                })
                    except Exception:
                        continue

    def write_recollection_log(self, output_file):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.reclaimed, f, indent=4)

# Example use:
# key = Wyrmkey("C:/Halcyon/memory_depth")
# key.scan()
# key.write_recollection_log("C:/Halcyon/recollections/recovered_fragments.json")
