
import os
import json
import yaml
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'personality'))
from veil_identity import activate_veil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONSTRUCTS_DIR = BASE_DIR / "constructs"
REGISTRY_FILE = CONSTRUCTS_DIR / "construct_registry.json"

def load_registry():
    if not REGISTRY_FILE.exists():
        print("Registry file not found.")
        return {}
    with open(REGISTRY_FILE, 'r') as f:
        return json.load(f)

def load_construct_metadata(name):
    metadata_path = CONSTRUCTS_DIR / name / "construct.yaml"
    if not metadata_path.exists():
        return None
    with open(metadata_path, 'r') as f:
        return yaml.safe_load(f)

def describe_construct(name):
    data = load_construct_metadata(name)
    if not data:
        print(f"No metadata found for construct: {name}")
        return
    print(f"\n[{name.upper()}]")
    for key, value in data.items():
        print(f"{key.capitalize()}: {value}")
    print()

def list_constructs(registry):
    print("\nRegistered Constructs:")
    for name, meta in registry.items():
        print(f"- {name} ({meta['state']})")

def main():
    veil = activate_veil()
    print(f"[VEIL ACTIVE] {veil['identity']} — {veil['signature']}")
    print("Welcome to Halcyon Core Interface")
    
    registry = load_registry()
    if not registry:
        return

    while True:
        print("\nCommands: list, describe <name>, exit")
        command = input(">> ").strip().lower()
        if command == "exit":
            break
        elif command == "list":
            list_constructs(registry)
        elif command.startswith("describe "):
            _, name = command.split(maxsplit=1)
            describe_construct(name)
        else:
            print("Unknown command.")

if __name__ == "__main__":
    main()
