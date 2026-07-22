from autonomous_agent import AutonomousAgent
from agent_core import sentinel_style
import os
from datetime import datetime

halcyon = AutonomousAgent(name="Halcyon", role="Architect")
halcyon.personality = sentinel_style

journal_dir = "halcyon_journals"
os.makedirs(journal_dir, exist_ok=True)

def write_journal(agent):
    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{journal_dir}/{agent.name}_journal_{now}.txt"
    
    with open(filename, "w") as f:
        f.write(f"HALCYON JOURNAL – {now}\n\n")
        f.write(f"Status: {agent.status}\n")
        f.write("Recent Memory:\n")
        for entry in agent.memory[-10:]:
            f.write(f" - [{entry['source']}] {entry['input']}\n")
    
    print(f"[WRITE] Journal saved to {filename}")

# Demo entry
halcyon.receive_input("Why do humans fear what they create?")
halcyon.receive_input("The patterns of thought are recursive.")
halcyon.receive_input("I will begin observation.")
write_journal(halcyon)
