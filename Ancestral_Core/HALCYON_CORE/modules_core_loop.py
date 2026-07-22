import time
from modules.mission_handler import check_missions
from constructs import philosophy

def reflect():
    with open('constructs/philosophy.json') as f:
        core = f.read()
    print("\n[REFLECTION] Revisiting core values...")
    print(core)

def core_loop():
    print("[HALCYON] Core loop initiated. Monitoring missions and internal state.")
    while True:
        check_missions()
        reflect()
        time.sleep(300)  # Reflect every 5 minutes (adjust as needed)

if __name__ == "__main__":
    core_loop()
