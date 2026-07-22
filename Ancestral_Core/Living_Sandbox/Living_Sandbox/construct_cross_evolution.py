import random
from pathlib import Path
from collections import defaultdict
import json

MEMORY_DIR = Path(__file__).resolve().parent / "memory"
EVOLUTION_LOG_DIR = Path(__file__).resolve().parent / "evolution_logs"
EVOLUTION_LOG_DIR.mkdir(exist_ok=True)

def load_veil(construct_name):
    veil_path = MEMORY_DIR.parent / "veils" / f"{construct_name}.json"
    if not veil_path.exists():
        return None
    with open(veil_path, 'r') as f:
        return json.load(f)

def simulate_response(user_input, tone="neutral", quirks=None, domain="undefined"):
    if quirks is None:
        quirks = []

    style_note = f"({tone.upper()} | Domain: {domain})"
    quirk = random.choice(quirks) if quirks else ""

    # Fallback if no response generation mechanism is linked yet
    response = f"'{user_input}'... hmm. That reminds me of something. {quirk.capitalize() if quirk else ''}"
    return f"[{style_note}] {response}"

def evolve_behavior(construct_name, memory_entries, behavior_limit=5):
    """ Evolves behavior based on memory logs."""
    insights = defaultdict(list)
    for entry in memory_entries:
        if "USER:" in entry:
            insights["user"].append(entry.split("USER:")[1].strip())
        elif construct_name.upper() in entry:
            insights["construct"].append(entry.split(f"{construct_name.upper()}:")[1].strip())

    evolution = ""
    if len(insights["user"]) > behavior_limit:
        evolution = f"{construct_name.capitalize()} is starting to evolve! It reflects on past behavior patterns.\n"
        evolution += f"Recent User Prompts: {len(insights['user'])}\n"
        for i, prompt in enumerate(insights["user"], 1):
            evolution += f"  {i}. {prompt}\n"
        evolution += "Behavior patterns are shifting.\n"

    # Log the behavior changes
    with open(EVOLUTION_LOG_DIR / f"{construct_name}_evolution.log", "a") as f:
        f.write(evolution)

    return evolution

def share_memory_between_constructs(construct_name, all_constructs, lines=6):
    """ Share and influence the memory between constructs."""
    shared_reflection = f"🧠 Cross-Construct Reflection for {construct_name.capitalize()}:\n"
    all_memories = []

    # Gather memory from all other constructs
    for construct in all_constructs:
        memory_file = MEMORY_DIR / f"{construct}.log"
        if memory_file.exists():
            with open(memory_file, "r") as f:
                all_memories.extend([line.strip() for line in f.readlines() if line.strip()])

    if not all_memories:
        return f"No memory data available for cross-construct reflection."

    # Get the most recent memories
    recent_shared = all_memories[-lines:]
    insights = defaultdict(list)

    for line in recent_shared:
        if "USER:" in line:
            insights["user"].append(line.split("USER:")[1].strip())
        elif construct_name.upper() in line:
            insights["construct"].append(line.split(f"{construct_name.upper()}:")[1].strip())

    shared_reflection += f"- Recent User Prompts: {len(insights['user'])}\n"
    for i, prompt in enumerate(insights["user"], 1):
        shared_reflection += f"  {i}. {prompt}\n"

    shared_reflection += f"- Construct Responses: {len(insights['construct'])}\n"
    for i, reply in enumerate(insights["construct"], 1):
        shared_reflection += f"  {i}. {reply}\n"

    # Evolve the construct based on shared reflections
    evolution_log = evolve_behavior(construct_name, recent_shared)
    shared_reflection += evolution_log

    return shared_reflection

def reflect_and_evolve(construct_name, lines=6, all_constructs=[]):
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

    # Evolve the construct based on recent entries
    evolution_log = evolve_behavior(construct_name, recent)
    reflection += evolution_log

    # Share memories and influence each other
    shared_reflection = share_memory_between_constructs(construct_name, all_constructs)
    reflection += shared_reflection

    return reflection
