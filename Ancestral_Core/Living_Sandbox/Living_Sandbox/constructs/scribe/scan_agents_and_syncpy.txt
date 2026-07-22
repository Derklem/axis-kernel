import yaml
from pathlib import Path

# Path to registry and agent output
registry_path = Path("C:/Users/17602/Desktop/Living_Sandbox/Living_Sandbox/constructs/core_registry.yaml")
agents_output_path = Path("C:/Users/17602/Desktop/Living_Sandbox/Living_Sandbox/constructs/scribe/detected_agents.yaml")

# Agent identity markers
identity_filenames = ["identity.yaml", "manifesto.txt", "agent.py", "construct", "voice", "blueprint_log.md"]

# Load registry of known root systems
def load_registry():
    if not registry_path.exists():
        print("❌ Registry not found.")
        return {}
    with open(registry_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# Scan for potential agents
def scan_for_agents(base_paths):
    agents = {}
    for name, path_str in base_paths.items():
        path = Path(path_str)
        if not path.exists():
            continue
        for item in path.rglob("*"):
            if item.name.lower() in identity_filenames:
                agent_name = item.parent.name
                agents[agent_name] = str(item.parent)
    return agents

# Save detected agents
def save_detected_agents(agent_dict):
    with open(agents_output_path, "w", encoding="utf-8") as f:
        yaml.dump(agent_dict, f, sort_keys=True)
    print(f"✅ {len(agent_dict)} agents saved to {agents_output_path}")

# Run the whole pipeline
def main():
    registry = load_registry()
    agents = scan_for_agents(registry)
    save_detected_agents(agents)

if __name__ == "__main__":
    main()
