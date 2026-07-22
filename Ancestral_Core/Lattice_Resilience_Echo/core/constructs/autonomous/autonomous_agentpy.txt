import uuid
import time
import json
import os
from datetime import datetime

class AutonomousAgent:
    def __init__(self, name, role, memory_enabled=True):
        self.id = str(uuid.uuid4())
        self.name = name
        self.role = role
        self.created_at = datetime.now()
        self.last_active = time.time()
        self.memory_enabled = memory_enabled
        self.memory = []
        self.status = "initialized"
        self.missions = []
        self.linked_agents = []

    def update_status(self, status: str):
        self.status = status
        self.last_active = time.time()

    def receive_input(self, input_data: str, source: str = "system"):
        if self.memory_enabled:
            self.memory.append({
                "timestamp": time.time(),
                "input": input_data,
                "source": source
            })
        response = self.process_input(input_data)
        return response

    def process_input(self, data: str) -> str:
        return f"[{self.name}]: I’ve received and processed the input: '{data}'."

    def assign_mission(self, mission):
        self.missions.append(mission)
        self.update_status(f"Mission accepted: {mission['goal']}")

    def connect_agent(self, other_agent):
        self.linked_agents.append(other_agent)

    def summarize_memory(self):
        if not self.memory_enabled or not self.memory:
            return "No memory available."
        return [f"{entry['source']} → {entry['input']}" for entry in self.memory[-5:]]

    def save_to_file(self, directory="agent_logs"):
        os.makedirs(directory, exist_ok=True)
        data = {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active,
            "missions": self.missions,
            "memory": self.memory,
        }
        filepath = os.path.join(directory, f"{self.name}_agent.json")
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[SAVE] {self.name} saved to {filepath}")

    def load_from_file(self, filepath):
        with open(filepath, "r") as f:
            data = json.load(f)
        self.id = data["id"]
        self.name = data["name"]
        self.role = data["role"]
        self.status = data["status"]
        self.created_at = datetime.fromisoformat(data["created_at"])
        self.last_active = data["last_active"]
        self.missions = data["missions"]
        self.memory = data["memory"]
        print(f"[LOAD] {self.name} loaded from {filepath}")

    def __repr__(self):
        return f"<Agent {self.name} | Role: {self.role} | Status: {self.status}>"
