
import subprocess
import time

def run_loop():
    while True:
        print("[🌀] Halcyon enters dream loop...")
        subprocess.run(["python", "halcyon_dream_loop.py"], check=False)
        print("[🌉] Harmonizing...")
        subprocess.run(["python", "halcyon_harmonizer.py"], check=False)
        print("[⏳] Sleeping for 1 hour...")
        time.sleep(3600)

if __name__ == "__main__":
    run_loop()
