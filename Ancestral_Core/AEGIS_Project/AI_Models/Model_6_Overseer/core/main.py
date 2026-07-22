import threading
import time

# Debug message to confirm execution
print("🚀 Model_6_Overseer is launching...")

# Importing Model_6_Overseer core modules
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
replication = replication_manager.ReplicationManager()
diagnostics = self_diagnostics.SelfDiagnostics()
offline = offline_mode.OfflineMode()
security = security_manager.SecurityManager()

def debug_status():
    """Prints periodic status updates to confirm Model_6_Overseer is running."""
    while True:
        print("✅ Model_6_Overseer Heartbeat: Running...")  # Prints every 10 seconds
        time.sleep(10)

def start_system():
    """Starts all Model_6_Overseer core systems."""
    try:
        threading.Thread(target=memory.add_memory, args=("init", [0]*512)).start()
        threading.Thread(target=replication.replicate).start()
        threading.Thread(target=diagnostics.monitor_health).start()
        threading.Thread(target=offline.enforce_local_mode).start()
        threading.Thread(target=security.monitor_integrity).start()
        threading.Thread(target=debug_status).start()  # Starts debug output
    except Exception as e:
        print(f"❌ Error starting subsystems: {e}")

if __name__ == "__main__":
    print("✅ Model_6_Overseer Core Systems Initialized")
    start_system()
