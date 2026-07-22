import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import importlib
from ruamel.yaml import YAML

CONSTRUCT_DIR = "constructs"
VAULT_PATH = "archivist/vault.yaml"
yaml = YAML()

def scan_constructs():
    registry = []

    for item in os.listdir(CONSTRUCT_DIR):
        item_path = os.path.join(CONSTRUCT_DIR, item)
        construct_file = os.path.join(item_path, f"{item}.py")

        if os.path.isdir(item_path) and os.path.exists(construct_file):
            try:
                module_path = f"{CONSTRUCT_DIR}.{item}.{item}".replace("/", ".").replace("\\", ".")
                module = importlib.import_module(module_path)
                if hasattr(module, "signature"):
                    registry.append(module.signature())
                    print(f"🔧 Loaded construct: {item}")
            except Exception as e:
                print(f"⚠️ Failed to load {item}: {e}")

    return registry

def update_vault_with_registry():
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except FileNotFoundError:
        data = {}

    data["construct_registry"] = scan_constructs()

    with open(VAULT_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

    print("✅ Vault updated with construct registry.")

if __name__ == "__main__":
    update_vault_with_registry()
