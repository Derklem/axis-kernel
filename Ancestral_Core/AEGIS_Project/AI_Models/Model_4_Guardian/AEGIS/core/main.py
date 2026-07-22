import threading
import memory_manager
import replication_manager
import self_diagnostics
import offline_mode
import security_manager

def start_system():
    """Starts all AEGIS core systems."""
    threading.Thread(target=memory_manager.memory).start()
    threading.Thread(target=replication_manager.replication).start()
    threading.Thread(target=self_diagnostics.diagnostics).start()
    threading.Thread(target=offline_mode.offline).start()
    threading.Thread(target=security_manager.security).start()

if __name__ == "__main__":
    print("🚀 AEGIS is launching...")
    start_system()
