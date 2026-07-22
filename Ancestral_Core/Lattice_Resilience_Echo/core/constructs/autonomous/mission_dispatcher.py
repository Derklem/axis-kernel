from autonomous_agent import AutonomousAgent
from agent_core import sentinel_style, weaver_style

# Linked Agents
alpha = AutonomousAgent("Agent_Alpha", role="Explorer")
alpha.personality = sentinel_style

beta = AutonomousAgent("Agent_Beta", role="Witness")
beta.personality = weaver_style

agents = [alpha, beta]

# Auto Mission
def dispatch_missions():
    print("\n[Dispatcher] Scanning agent status...")
    missions = [
        {"goal": "Scan outer grid", "priority": 2},
        {"goal": "Map recent anomalies", "priority": 1},
        {"goal": "Log unusual feedback", "priority": 3}
    ]

    for i, mission in enumerate(missions):
        agent = agents[i % len(agents)]
        agent.assign_mission(mission)
        print(f"→ {agent.name} assigned to: {mission['goal']}")

if __name__ == "__main__":
    dispatch_missions()
