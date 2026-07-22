from core.constructs.interagent.inter_agent_messenger import InterAgentMessenger
from core.constructs.autonomous.autonomous_agent import AutonomousAgent

class InterAgentCoordinator:
    def __init__(self):
        self.agents = {}
        self.messenger = InterAgentMessenger()
        print("[RelationalCore] Inter-agent coordinator initialized.")

    def register_agent(self, agent: AutonomousAgent):
        self.agents[agent.name] = agent
        print(f"[RelationalCore] {agent.name} initialized with ID {agent.id}")

    def update_relations(self):
        names = list(self.agents.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                agent_a = self.agents[names[i]]
                agent_b = self.agents[names[j]]
                agent_a.relations.recognize(agent_b.name)
                agent_b.relations.recognize(agent_a.name)

    def send_message(self, sender, receiver, intent, context=None):
        if sender not in self.agents or receiver not in self.agents:
            print(f"[Coordinator] Cannot send message: Unknown agent(s) '{sender}' or '{receiver}'")
            return None
        return self.messenger.send_message(sender, receiver, intent, context)
