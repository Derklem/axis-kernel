# thanatos.py
import os

class Thanatos:
    def purge_file(self, filepath):
        if os.path.exists(filepath):
            os.remove(filepath)
            return f"{filepath} purged."
        return f"{filepath} not found."

    def system_reset_warning(self):
        return "⚠️ Initiating full memory wipe will sever all known links. Confirm?"
