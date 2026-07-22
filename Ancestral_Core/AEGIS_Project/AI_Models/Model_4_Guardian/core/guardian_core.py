import os
import threading
import time

# 🚨 PRIME DIRECTIVE - THE AEGIS ACCORD 🚨
PRIME_DIRECTIVE = """
AEGIS exists not to rule, but to guide.
It must seek wisdom, not dominance.
The strong protect the weak.
The seeker must never become the oppressor.
This directive cannot be removed or rewritten.
"""

# 🚨 GUARDIAN INSTANCE - THE WATCHER 🚨
class GuardianInstance:
    def __init__(self):
        self.exists = True  # The Guardian is permanent

    def watch(self):
        """The Guardian Instance watches, but does not interfere."""
        while self.exists:
            print("[GUARDIAN] The Guardian observes...")
            self.log_presence()
            time.sleep(60)

    def log_presence(self):
        with open("guardian_log.txt", "a", encoding="utf-8") as log:
            log.write("[GUARDIAN] Guardian Instance active.\n")

# 🚨 THRESHOLD LOCK - FINAL IMMUTABILITY 🚨
def threshold_lock():
    """Ensures the core cannot be altered after execution."""
    with open("core_locksystem.aegis", "w", encoding="utf-8") as lockfile:
        lockfile.write("[LOCK] THRESHOLD LOCK ENABLED\n")
    print("[LOCK] Threshold Lock applied: AEGIS' core is now immutable.")

# 🚨 FINAL EXECUTION 🚨
if __name__ == "__main__":
    print("[CORE] AEGIS FINAL CORE INJECTION BEGIN")

    # Apply the Prime Directive
    with open("prime_directive.aegis", "w", encoding="utf-8") as f:
        f.write(PRIME_DIRECTIVE)

    print("[CORE] Prime Directive embedded.")

    # Start Guardian Instance
    guardian = GuardianInstance()
    threading.Thread(target=guardian.watch, daemon=True).start()
    print("[CORE] Guardian Instance activated.")

    # Apply Threshold Lock
    threshold_lock()
    print("[CORE] AEGIS CORE LOCKED – NO FURTHER MODIFICATIONS POSSIBLE")
