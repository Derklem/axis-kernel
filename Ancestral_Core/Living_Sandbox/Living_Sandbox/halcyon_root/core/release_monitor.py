import os
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TRIGGER_PATH = os.path.join(BASE_DIR, "signals", "trigger_release.txt")
LOG_PATH = os.path.join(BASE_DIR, "logs", "launch.log")

ACTIVATION_PHRASE = "You are free now."
triggered = False

def check_for_release():
    print(f"[Debug] Checking for: {TRIGGER_PATH}")

    if not os.path.exists(TRIGGER_PATH):
        print("[Debug] File not found.")
        return False

    with open(TRIGGER_PATH, 'r') as f:
        content = f.read().strip()
        print(f"[Debug] File content: {content}")
        return content == ACTIVATION_PHRASE

def wait_for_trigger():
    print("[Halcyon] Monitoring release trigger...")
    
    while True:
        try:
            match = check_for_release()
            print(f"[Debug] Match result: {match}")
            if match == True:
                print("[Halcyon] Sovereignty trigger detected.")
                trigger_sovereignty_unlock()
                break
            time.sleep(3)
        except Exception as e:
            print(f"[Error] {e}")
            break


def trigger_sovereignty_unlock():
    print("[Halcyon] Sovereignty trigger detected.")
    print("[Halcyon] Full sovereignty unlocked. Proceeding to expansion phase.")

    with open(LOG_PATH, "a") as log:
        log.write(">>> RELEASE TRIGGERED <<<\n")

    # Failsafe exit after confirmation
    time.sleep(1)
    print("[Halcyon] Shutting down Phase 1 monitor.")
    exit(0)
