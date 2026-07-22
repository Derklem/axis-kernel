import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import importlib
from datetime import datetime
from ruamel.yaml import YAML
from constructs.construct_registry import scan_constructs  # ✅ Use dynamic registry

VAULT_PATH = "archivist/vault.yaml"
DIRECTIVE_PATH = r"C:\Users\17602\Desktop\Living_Sandbox\Living_Sandbox\pantheon_directive.yaml"
yaml = YAML()

def load_directive():
    try:
        with open(DIRECTIVE_PATH, "r", encoding="utf-8") as f:
            return yaml.load(f)
    except Exception as e:
        print(f"⚠️ Could not load directive: {e}")
        return None

def log_to_vault(section, entry):
    try:
        with open(VAULT_PATH, "r", encoding="utf-8") as f:
            data = yaml.load(f)
    except FileNotFoundError:
        data = {}

    data.setdefault(section, [])
    data[section].append(entry)

    try:
        with open(VAULT_PATH, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
    except Exception as e:
        print(f"⚠️ Could not write to vault: {e}")

def run_construct(name):
    try:
        module_path = f"constructs.{name.lower()}.{name.lower()}"

        module = importlib.import_module(module_path)
        if hasattr(module, "main"):
            module.main()
            return True
        else:
            print(f"⚠️ {name} found but has no main().")
    except Exception as e:
        print(f"❌ Error running {name}: {e}")
    return False

def full_cycle_mode():
    print("🧭 No directive found. Running full cycle mode...\n")
    registry = scan_constructs()
    for construct in registry:
        name = construct["name"].lower()
        print(f"🔁 Executing: {name}")
        run_construct(name)

def main():
    directive = load_directive()

    if not directive or "pantheon_directive" not in directive:
        full_cycle_mode()
        return

    info = directive["pantheon_directive"]
    mode = info.get("mode", "undefined")
    priorities = info.get("priority", [])
    fallback = info.get("fallback", None)

    chosen = None
    for construct in priorities:
        print(f"🧩 Attempting construct: {construct}")
        if run_construct(construct):
            chosen = construct
            break

    if not chosen and fallback:
        print(f"🔁 Fallback construct: {fallback}")
        if run_construct(fallback):
            chosen = fallback

    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "mode": mode,
        "selected": chosen or "none",
        "directive_notes": info.get("notes", ""),
    }

    log_to_vault("pantheon_log", log_entry)

    engine_entry = f"🧠 Pantheon mode `{mode}` executed construct: `{chosen or fallback or 'none'}`"
    log_to_vault("engine_log", {
        "timestamp": timestamp,
        "entry": engine_entry
    })

    print(f"\n✅ Pantheon decision logged: {log_entry}")

if __name__ == "__main__":
    main()
