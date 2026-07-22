from core.constructs.autonomous.autonomous_agent import AutonomousAgent
from core.constructs.interagent.inter_agent_coordinator import InterAgentCoordinator

coordinator = InterAgentCoordinator()

def register_agent(name="Agent_X", role="Generic"):
    agent = AutonomousAgent(name=name, role=role)
    coordinator.register_agent(agent)
    print(f"[Registry] Registered agent: {agent.name} | Role: {agent.role}")
    return agent
