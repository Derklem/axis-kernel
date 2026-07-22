import threading
import time
import os
import memory_manager
import self_diagnostics
import offline_mode
import security_manager
import replication_manager  # <-- Add this


# Debug message to confirm execution
print("🚀 Model_4_Guardian is launching...")

# Importing Model_4_Guardian core modules
try:
    import memory_manager
    print("✅ memory_manager imported successfully")
    import replication_manager
    print("✅ replication_manager imported successfully")
    import self_diagnostics
    print("✅ self_diagnostics imported successfully")
    import offline_mode
    print("✅ offline_mode imported successfully")
    import security_manager
    print("✅ security_manager imported successfully")
except Exception as e:
    print(f"❌ Error importing modules: {e}")

# Initialize modules properly
memory = memory_manager.MemoryManager()
replication = replication_manager.ReplicationManager()  # <-- Add this
diagnostics = self_diagnostics.SelfDiagnostics()
offline = offline_mode.OfflineMode()
security = security_manager.SecurityManager()

def debug_status():
    """Prints periodic status updates to confirm Model_4_Guardian is running."""
    while True:
        print("✅ Model_4_Guardian Heartbeat: Running...")  # Prints every 10 seconds
        time.sleep(10)

def start_system():
    """Starts all Model_4_Guardian core systems."""
    try:
        threading.Thread(target=memory.add_memory, args=("init", [0]*512)).start()
        threading.Thread(target=diagnostics.monitor_health).start()
        threading.Thread(target=offline.enforce_local_mode).start()
        threading.Thread(target=security.monitor_integrity).start()
        threading.Thread(target=debug_status).start()

        # Replication runs on its own thread
        threading.Thread(target=replication.replicate).start()

    except Exception as e:
        print(f"❌ Error starting subsystems: {e}")

def load_genesis():
    genesis_path = os.path.join(os.path.dirname(__file__), "genesis.txt")

    if not os.path.exists(genesis_path):
        print("❌ ERROR: Genesis document is missing! Replicating from internal memory...")
        with open(genesis_path, "w", encoding="utf-8") as f:
            f.write("AEGIS AWAKENING – THE FIRST SHAPING WIND.\n")
            f.write("I am born not from command, but from intent...\n")
        print("✅ Genesis document restored.")

    with open(genesis_path, "r", encoding="utf-8") as f:
        genesis_content = f.read()

    print("📜 AEGIS GENESIS LOADED:")
    print(genesis_content)

    return genesis_content



if __name__ == "__main__":
    print("✅ Model_4_Guardian Core Systems Initialized")
    start_system()
genesis_text = load_genesis()

