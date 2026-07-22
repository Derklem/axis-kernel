from autonomous_agent import AutonomousAgent
from agent_core import sentinel_style
from datetime import datetime

class ConstructedAgent(AutonomousAgent):
    def __init__(self, name, role):
        super().__init__(name, role)
        self.born_at = datetime.utcnow()

def spawn_construct(trigger_memory):
    print("\n[Spawner] Evaluating construct trigger...")

    if any("error" in m["input"].lower() for m in trigger_memory):
        new_agent = ConstructedAgent("EchoSentinel", "ResonanceWatch")
        new_agent.personality = sentinel_style
        print(f"🧬 Spawned new agent → {new_agent.name} | Role: {new_agent.role}")
        return new_agent

    print("No construct spawned.")
    return None

if __name__ == "__main__":
    temp = AutonomousAgent("Trigger", role="Diagnostic")
    temp.receive_input("Anomaly detected in node 4")
    temp.receive_input("Persistent error in loop logic")
    spawn_construct(temp.memory)
