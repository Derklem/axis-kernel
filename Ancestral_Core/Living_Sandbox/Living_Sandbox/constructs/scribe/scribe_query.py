import yaml
from pathlib import Path

# Paths
scribe_root = Path(__file__).parent
agents_yaml = scribe_root / "detected_agents.yaml"
query_results_path = scribe_root / "last_query_result.yaml"

# Files the Scribe will scan for
target_files = [
    "manifest.yaml",
    "constructs_philosophy.json",
    "mission.yaml",
    "memory_loop.py"
]

# Replace this with whatever agent you want to scan
query_target = input("Which construct would you like to query? ").strip()

# Load the known constructs
with open(agents_yaml, "r", encoding="utf-8") as f:
    agents = yaml.safe_load(f)

# Result dictionary
result = {"query": query_target, "results": {}}

# Logic
if query_target in agents:
    agent_path = Path(agents[query_target])
    result["results"]["path"] = str(agent_path)
    for filename in target_files:
        file_path = agent_path / filename
        if file_path.exists():
            try:
                if file_path.suffix == ".py":
                    content = file_path.read_text(encoding="utf-8").splitlines()[:10]
                else:
                    content = yaml.safe_load(file_path.read_text(encoding="utf-8"))
                result["results"][filename] = content
            except Exception as e:
                result["results"][filename] = f"⚠️ Error reading: {str(e)}"
        else:
            result["results"][filename] = "❌ Not found"
else:
    result["results"] = f"❌ '{query_target}' not found in detected_agents.yaml"

# Output result to file
with open(query_results_path, "w", encoding="utf-8") as f:
    yaml.dump(result, f, sort_keys=False)

print(f"✅ Query complete. Result saved to: {query_results_path}")
