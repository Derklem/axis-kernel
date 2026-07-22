from .autonomous_agent import AutonomousAgent
from core.learning.predictive_analysis import PredictiveAnalyzer  # Ensure this import exists

class AutonomousManager:
    def __init__(self):
        self.agents = []

    def create_agent(self, name):
        agent = AutonomousAgent(name)
        self.agents.append(agent)
        print(f"[AutonomousManager] Created and added new agent: {name}")
        return agent

    def assign_dynamic_task(self, agent_name, task):
        for agent in self.agents:
            if agent.name == agent_name:
                return agent.execute_task(task)
        print(f"[AutonomousManager] No agent found with name: {agent_name}")

    def manage_agents(self, learned_data=None):
        print("[AutonomousManager] Managing autonomous agents dynamically.")
        for agent in self.agents:
            if learned_data:
                task = self.decide_task_based_on_data(agent.name, learned_data)
                self.assign_dynamic_task(agent.name, task)
            else:
                self.assign_dynamic_task(agent.name, f"Dynamic Task for {agent.name}")

    def decide_task_based_on_data(self, agent_name, data):
        if 'AI' in data:
            return f"{agent_name}: Analyze latest AI developments"
        elif 'error' in data.lower():
            return f"{agent_name}: Resolve detected errors"
        else:
            return f"{agent_name}: Perform routine maintenance"

    # ADD THIS METHOD BELOW CLEARLY:
    def predictive_task_assignment(self, structured_data):
        analyzer = PredictiveAnalyzer()
        predictions = analyzer.analyze_and_predict(structured_data)

        for agent, prediction in zip(self.agents, predictions):
            self.assign_dynamic_task(agent.name, prediction)
