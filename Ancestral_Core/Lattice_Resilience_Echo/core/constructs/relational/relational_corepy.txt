import uuid
from datetime import datetime

class RelationalCore:
    def __init__(self, agent_name):
        self.agent_id = str(uuid.uuid4())
        self.name = agent_name
        self.trust_scores = {}  # {agent_name: score}
        self.history = []  # List of tuples: (event, agent_name, timestamp)
        print(f"[RelationalCore] {self.name} initialized with ID {self.agent_id}")

    def recognize_agent(self, other_agent_name):
        if other_agent_name not in self.trust_scores:
            self.trust_scores[other_agent_name] = 0.5  # Neutral trust
            print(f"[RelationalCore] {self.name} recognized new agent {other_agent_name}")

    def update_trust(self, other_agent_name, delta):
        self.trust_scores[other_agent_name] = min(1.0, max(0.0, self.trust_scores.get(other_agent_name, 0.5) + delta))
        print(f"[RelationalCore] {self.name} updated trust for {other_agent_name}: {self.trust_scores[other_agent_name]}")

    def log_interaction(self, event, other_agent_name):
        timestamp = datetime.utcnow().isoformat()
        self.history.append((event, other_agent_name, timestamp))
        print(f"[RelationalCore] {self.name} logged interaction with {other_agent_name}: {event} at {timestamp}")

    def get_trust_score(self, other_agent_name):
        return self.trust_scores.get(other_agent_name, 0.5)
