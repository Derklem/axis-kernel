import yaml
from pathlib import Path

# Registry file & agent output
registry_path = Path("C:/Users/17602/Desktop/Living_Sandbox/Living_Sandbox/constructs/core_registry.yaml")
agents_output_path = Path("C:/Users/17602/Desktop/Living_Sandbox/Living_Sandbox/constructs/scribe/detected_agents.yaml")

# New, smarter signature patterns
identity_signatures = [
    "constructs_philosophy.json",
    "identity.yaml",
    "persona.yaml",
    "soul.txt",
    "agent.py",
    "manifesto.txt"
]

def load_registry():
    if not registry_path.exists():
        print("❌ Registry not found.")
        return {}
    with open(registry_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def scan_for_agents(base_paths):
    agents = {}
    for name, path_str in base_paths.items():
        base = Path(path_str)
        if not base.exists():
            continue
        for item in base.rglob("*"):
            if item.name in identity_signatures:
                agent_id = item.parent.name
                agents[agent_id] = str(item.parent)
    return agents

def save_detected_agents(agent_dict):
    with open(agents_output_path, "w", encoding="utf-8") as f:
        yaml.dump(agent_dict, f, sort_keys=True)
    print(f"✅ {len(agent_dict)} agents saved to {agents_output_path}")

def main():
    registry = load_registry()
    agents = scan_for_agents(registry)
    save_detected_agents(agents)

if __name__ == "__main__":
    main()
