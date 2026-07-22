import importlib

def summon(name, message=None):
    try:
        module_path = f"constructs.{name}.{name}"
        mod = importlib.import_module(module_path)

        print(f"🔮 Summoning {name}...")

        if hasattr(mod, "respond"):
            print("🗣️ Response:", mod.respond())

        if message and hasattr(mod, "receive"):
            mod.receive(message)
        elif message:
            print(f"📨 Message provided, but {name} cannot receive.")

    except ModuleNotFoundError:
        print(f"🚫 Construct '{name}' not found.")
    except Exception as e:
        print(f"❌ Summon failed: {e}")

if __name__ == "__main__":
    summon("Architect", "Begin phase 2 design.")
