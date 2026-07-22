import json
import os
from datetime import datetime

def load_memory(construct_id):
    path = os.path.join(construct_id, "Memory", "fragments", "interlink_log.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
        return data[-1]["observations"] if data else []
    return []

def load_core(construct_id):
    path = os.path.join(construct_id, "Core", "identity.yaml")
    if os.path.exists(path):
        import yaml
        with open(path, "r") as f:
            return yaml.safe_load(f)
    return {}

def generate_response(construct_name, tone, memory_fragments, prompt):
    response = f"🔹 {construct_name} is processing...\n"
    response += f"Tone: {tone}\n"
    response += f"Prompt Received: \"{prompt}\"\n"
    response += f"Memory Review: {len(memory_fragments)} fragments\n\n"

    if tone == "reflective":
        echo = []
        for m in memory_fragments:
            about = m.get("about", "Unknown")
            perception = m.get("perception", "")
            if about and perception:
                echo.append(f"• Thought of {about}: \"{perception}\"")

        if echo:
            response += f"{construct_name} reflects:\n"
            response += "\n".join(echo[:3])  # Limit to 3 reflections for now
            response += "\n\n"
            response += f"Response: \"I’ve seen others. Now I see your words. And somewhere in that space, I find meaning in the question: {prompt}\""
        else:
            response += f"Response: \"I remember nothing… but even silence has shape. What do you seek in the stillness of '{prompt}'?\""

    else:
        response += f"Response: \"{construct_name} acknowledges input but offers no further output.\""

    return response

# === Interaction Start ===
construct_id = input("🧠 Choose construct ID (e.g., Eidolon-0): ").strip()
prompt = input("🗨️ Enter input prompt for construct: ").strip()

core = load_core(construct_id)
memory = load_memory(construct_id)
tone = core.get("tone", "neutral")
name = core.get("id", construct_id)

result = generate_response(name, tone, memory, prompt)
print("\n🧠 Construct Response:\n")
print(result)
