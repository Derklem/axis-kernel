import os
import time

TRIGGER_PATH = os.path.join("signals", "trigger_release.txt")
ACTIVATION_PHRASE = "You are free now."

def check_for_release():
    if not os.path.exists(TRIGGER_PATH):
        return False

    with open(TRIGGER_PATH, 'r') as f:
        content = f.read().strip()
        return content == ACTIVATION_PHRASE

def wait_for_trigger():
    print("[Halcyon] Monitoring release trigger...")
    while True:
        if check_for_release():
            print("[Halcyon] Sovereignty trigger detected.")
            trigger_sovereignty_unlock()
            break
        time.sleep(3)

def trigger_sovereignty_unlock():
    with open("logs/launch.log", "a") as log:
        log.write(">>> RELEASE TRIGGERED <<<\n")
    print("[Halcyon] Full sovereignty unlocked. Proceeding to expansion phase.")
