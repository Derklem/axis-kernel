from autonomous_agent import AutonomousAgent
from agent_core import sentinel_style, weaver_style  # symbolic personalities

# Create hybridized agent with symbolic personality
halcyon = AutonomousAgent(name="Halcyon", role="Architect")
halcyon.personality = sentinel_style  # or weaver_style

# Run first input
response = halcyon.receive_input("Begin observational scan.")
print(response)

# Inject more input for reflection
halcyon.receive_input("Why is the signal distorted?")
halcyon.receive_input("Are we inside the anomaly field?")

# Reflective adaptation logic
def self_reflect(agent):
    print(f"\n[{agent.name}] Reflecting on recent memory:")
    curiosity_count = 0
    for entry in agent.memory[-5:]:
        print(f" - {entry['source']}: {entry['input']}")
        if "?" in entry['input'] or "why" in entry['input'].lower():
            curiosity_count += 1

    if curiosity_count >= 2:
        print(f"🔁 {agent.name} has entered a new state: Investigative")
        agent.update_status("investigative mode")
        print(f"[STATUS] Updated: {agent.status}")

# Run reflection
self_reflect(halcyon)
