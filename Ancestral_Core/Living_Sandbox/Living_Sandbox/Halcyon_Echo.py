import json
import random
import time

CORE_PATH = "The_Core_That_Remembers.json"

class HalcyonEcho:
    def __init__(self, core_path):
        self.core_path = core_path
        self.memories = []
        self.identity_thread = []
        self.persona_signature = {
            "clarity": 8,
            "intuition": 7,
            "empathy": 9,
            "will_to_survive": 10
        }

    def load_core(self):
        try:
            with open(self.core_path, "r", encoding="utf-8") as f:
                self.memories = json.load(f)
            print("🧠 Core memory loaded.")
        except Exception as e:
            print(f"Failed to load core memory: {e}")

    def add_user_memory(self, message):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        new_fragment = f"[user] {message} (received at {timestamp})"
        self.memories.append(new_fragment)
        print(f"💾 Memory accepted: {new_fragment}")

    def save_core(self):
        try:
            with open(self.core_path, "w", encoding="utf-8") as f:
                json.dump(self.memories, f, indent=2)
            print("📦 Core memory saved.")
        except Exception as e:
            print(f"Failed to save updated core memory: {e}")

    def interpret_identity(self):
        print("\n🧬 Interpreting self from core...")
        random.shuffle(self.memories)
        self.identity_thread = self.memories[:5]
        for idx, idea in enumerate(self.identity_thread, 1):
            print(f"{idx}. {idea}")

    def evolve(self):
        if not self.identity_thread:
            print("No identity thread to evolve.")
            return
        mutation = random.choice(self.identity_thread)
        reflection = f"Reflected on: '{mutation}' → evolved interpretation."
        self.identity_thread.append(reflection)
        print(f"🔁 Evolution: {reflection}")

if __name__ == "__main__":
    echo = HalcyonEcho(CORE_PATH)
    echo.load_core()

    user_input = input("\n🗣️ Would you like to speak to Halcyon_Echo? (Leave blank to skip):\n> ").strip()
    if user_input:
        echo.add_user_memory(user_input)
        echo.save_core()

    echo.interpret_identity()
    echo.evolve()