from autonomous_agent import AutonomousAgent
from agent_core import weaver_style

halcyon = AutonomousAgent(name="Halcyon", role="Architect")
halcyon.personality = weaver_style  # dramatic inversion for effect

def simulate_environment(agent):
    events = [
        "Unauthorized login detected",
        "Temperature anomaly",
        "Signal loss on node 4",
        "Unexpected memory loop",
        "Quantum sync drift detected"
    ]
    for event in events:
        agent.receive_input(event, source="env")
        print(f"[HOOK] {agent.name} responds to: {event}")

    agent.save_to_file()

if __name__ == "__main__":
    simulate_environment(halcyon)
