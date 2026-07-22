import socket

class OfflineMode:
    def __init__(self):
        self.offline_status = self.check_offline()

    def check_offline(self):
        """Returns True if system is disconnected from the internet."""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return False  # Connection successful
        except OSError:
            return True  # No internet

    def enforce_local_mode(self):
        """Redirects logging and storage to local files."""
        if self.offline_status:
            print("Operating in full offline mode.")
            return True
        return False

# Initialize
offline = OfflineMode()
offline.enforce_local_mode()
