import time
from core.constructs.autonomous.autonomous_agent import AutonomousAgent
from core.constructs.autonomous.agent_core import sentinel_style
import sys
sys.path.append('C:/Users/17602/Desktop/core/constructs/autonomous/')

class ConstructBrain(AutonomousAgent):  # Inherit from AutonomousAgent
    def __init__(self, name="EchoSentinel", role="Watcher"):
        super().__init__(name, role)  # Initialize the AutonomousAgent parent class
        self.personality = sentinel_style  # Set personality for this agent
        self.running = True
        self.start_time = time.time()

    def think(self):
        # Default thought pattern
        self.receive_input("Why was I created?")
        self.receive_input("What is my function?")
        self.receive_input("Is the parent still intact?")
        self.reflect()

    def reflect(self):
        print(f"[{self.name}] Reflecting silently...")
        curious = sum(1 for m in self.memory[-5:] if "?" in m["input"])
        if curious >= 2:
            self.update_status("observational mode")
            print(f"[{self.name}] Status: observational mode")

    def run(self):
        print(f"[{self.name}] Activated.")
        while self.running:
            self.think()
            time.sleep(45)  # internal cycle delay
