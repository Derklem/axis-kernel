import os
import json
from datetime import datetime

BASE_DIR = "E:/Arcane Library/Arcane_Librarian/historical_data_archives/"
INDEX_FILE = "E:/Arcane Library/Arcane_Librarian/latent_search/historical_index.json"

def index_archives():
    records = []
    for root, dirs, files in os.walk(BASE_DIR):
        for f in files:
            full_path = os.path.join(root, f)
            record = {
                "path": full_path.replace("\\\\", "/"),
                "size": os.stat(full_path).st_size,
                "created": datetime.fromtimestamp(os.path.getctime(full_path)).isoformat()
            }
            records.append(record)

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

if __name__ == "__main__":
    index_archives()
