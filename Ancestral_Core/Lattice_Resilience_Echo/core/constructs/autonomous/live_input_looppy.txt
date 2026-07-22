from autonomous_agent import AutonomousAgent
from agent_core import sentinel_style

halcyon = AutonomousAgent("Halcyon", "Architect")
halcyon.personality = sentinel_style

print("🔹 LIVE HALCYON INTERFACE 🔹")
print("Type thoughts below. Type 'exit' to quit.\n")

while True:
    user_input = input("🧠 > ")
    if user_input.lower() in ["exit", "quit"]:
        break

    response = halcyon.receive_input(user_input, source="manual")
    print(f"{response}")
