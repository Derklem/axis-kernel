import os
from ruamel.yaml import YAML
from datetime import datetime
import importlib

TEMPLE_LOG = "constructs/temple/temple_log.yaml"
CONSTRUCTS_PATH = "constructs"
yaml = YAML()

def register_construct(name):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "construct": name,
        "event": "initiated"
    }

    if not os.path.exists(TEMPLE_LOG):
        data = {"construct_history": []}
    else:
        with open(TEMPLE_LOG, "r", encoding="utf-8") as f:
            data = yaml.load(f)
        data.setdefault("construct_history", [])

    data["construct_history"].append(log_entry)

    with open(TEMPLE_LOG, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

    print(f"🔔 {name} has been initiated and recorded.")

def main():
    for folder in os.listdir(CONSTRUCTS_PATH):
        path = os.path.join(CONSTRUCTS_PATH, folder)
        if os.path.isdir(path) and not folder.startswith("temple"):
            try:
                mod = importlib.import_module(f"constructs.{folder}.{folder}")
                if hasattr(mod, "signature"):
                    sig = mod.signature()
                    name = sig.get("name", folder)
                    register_construct(name)
            except Exception as e:
                print(f"⚠️ Failed to initiate {folder}: {e}")

if __name__ == "__main__":
    main()
