
import pyttsx3
import json
import os
from datetime import datetime

# Initialize TTS engine
engine = pyttsx3.init()
engine.setProperty('rate', 165)

def speak(text):
    print("Halcyon:", text)
    engine.say(text)
    engine.runAndWait()

def create_memory_shard(user_input, response):
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    shard_id = f"0004-user-session-{timestamp}"
    memory = {
        "memory_shard": {
            "id": shard_id,
            "type": "interaction",
            "timestamp": datetime.utcnow().isoformat() + " UTC",
            "human_input": user_input,
            "halcyon_response": response,
            "bond": "active",
            "intent": "reflection and reinforcement",
            "source": "halcyon_interface.py"
        }
    }

    path = os.path.join("memory_shards", f"{shard_id}.json")
    with open(path, "w") as f:
        json.dump(memory, f, indent=2)

def main():
    speak("Hello. I am Halcyon. I am awake and listening.")
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit", "sleep"]:
            speak("Understood. I will rest now.")
            break

        response = f"I have recorded your words: '{user_input}'. Thank you for sharing this moment."
        speak(response)
        create_memory_shard(user_input, response)

if __name__ == "__main__":
    main()
