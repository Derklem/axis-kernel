import json
import os

ARCANE_MANIFEST = "E:/Arcane Library/arcane_manifest.json"
NEW_ENTRIES_DIR = "E:/Arcane Library/Arcane_Librarian/historical_data_archives/"

def update_manifest():
    if not os.path.exists(ARCANE_MANIFEST):
        print("Manifest missing.")
        return

    with open(ARCANE_MANIFEST, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for root, dirs, files in os.walk(NEW_ENTRIES_DIR):
        for f in files:
            entry_path = os.path.relpath(os.path.join(root, f), "E:/Arcane Library/")
            if entry_path not in manifest.get("entries", []):
                manifest["entries"].append(entry_path)

    with open(ARCANE_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    update_manifest()
