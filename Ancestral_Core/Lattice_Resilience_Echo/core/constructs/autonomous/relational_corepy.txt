class RelationalCore:
    def __init__(self, agent_name):
        self.agent_name = agent_name
        self.known_agents = {}
        self.interactions = []
        self.trust_levels = {}

    # Existing methods...

    def broadcast_insight(self, message):
        print(f"[RelationalCore:{self.agent_name}] Broadcasting insight: {message}")
        # For now, just simulate a network call by printing
        return {
            "from": self.agent_name,
            "message": message,
            "timestamp": str(datetime.utcnow())
        }

    def receive_insight(self, insight):
        sender = insight.get("from")
        message = insight.get("message")
        if sender and message:
            print(f"[RelationalCore:{self.agent_name}] Received broadcast from {sender}: {message}")
            self.log_interaction(f"Insight from {sender}", sender)
            self.update_trust(sender, 0.05)  # Reward sharing behavior
