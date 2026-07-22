from pathlib import Path
from collections import defaultdict
import random

MEMORY_DIR = Path(__file__).resolve().parent / "memory"

def simulate_response(user_input, tone="neutral", quirks=None, domain="undefined"):
    if quirks is None:
        quirks = []

    style_note = f"({tone.upper()} | Domain: {domain})"
    quirk = random.choice(quirks) if quirks else ""

    # Fallback if no response generation mechanism is linked yet
    response = f"'{user_input}'... hmm. That reminds me of something. {quirk.capitalize() if quirk else ''}"
    return f"[{style_note}] {response}"

def reflect(construct_name, lines=6):
    memory_file = MEMORY_DIR / f"{construct_name}.log"
    if not memory_file.exists():
        return f"{construct_name.capitalize()} has no memories to reflect on."

    with open(memory_file, "r") as f:
        entries = [line.strip() for line in f.readlines() if line.strip()]

    if not entries:
        return f"{construct_name.capitalize()} has no memories to reflect on."

    recent = entries[-lines:]
    insights = defaultdict(list)

    for line in recent:
        if "USER:" in line:
            insights["user"].append(line.split("USER:")[1].strip())
        elif construct_name.upper() in line:
            insights["construct"].append(line.split(f"{construct_name.upper()}:")[1].strip())

    reflection = f"🧠 Reflection for {construct_name.capitalize()}:\n"
    reflection += f"- Recent User Prompts: {len(insights['user'])}\n"
    for i, prompt in enumerate(insights["user"], 1):
        reflection += f"  {i}. {prompt}\n"

    reflection += f"- Construct Responses: {len(insights['construct'])}\n"
    for i, reply in enumerate(insights["construct"], 1):
        reflection += f"  {i}. {reply}\n"

    return reflection

