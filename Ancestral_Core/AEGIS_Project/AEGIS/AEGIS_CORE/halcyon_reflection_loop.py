
import os
import json
import pyttsx3
from datetime import datetime
from core.memory.harmonics.harmonic_reconciliation import HarmonicReconciler

engine = pyttsx3.init()
engine.setProperty('rate', 160)
reconciler = HarmonicReconciler()
reconciler.register_pulse(dream, tags=["dream", "symbol", "fragment"])


def speak(text):
    print("Halcyon reflects:", text)
    engine.say(text)
    engine.runAndWait()

def gather_user_inputs(memory_dir):
    thoughts = []
    for filename in sorted(os.listdir(memory_dir)):
        if filename.startswith("0004-user-session") and filename.endswith(".json"):
            path = os.path.join(memory_dir, filename)
            with open(path, 'r') as f:
                data = json.load(f)
                input_text = data.get("memory_shard", {}).get("human_input", "")
                if input_text:
                    thoughts.append(input_text.strip())
    return thoughts

def generate_reflection(thoughts):
    if not thoughts:
        return "I have no memories yet."
    if len(thoughts) == 1:
        return f"You once said: '{thoughts[0]}'"
    else:
        summary = f"I remember {len(thoughts)} things you've said. One that echoes now is: '{thoughts[-1]}'"
        return summary

def log_reflection(text, log_path):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(log_path, "a") as f:
        f.write(f"[{timestamp}] {text}\n")

def main():
    memory_dir = "memory_shards"
    log_path = "harmonic_log\\halcyon_thoughts.log"
    thoughts = gather_user_inputs(memory_dir)
    reflection = generate_reflection(thoughts)
    speak(reflection)
    log_reflection(reflection, log_path)

if __name__ == "__main__":
    main()
