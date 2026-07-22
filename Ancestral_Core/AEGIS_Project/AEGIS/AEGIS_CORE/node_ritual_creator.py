
import json
import os
import uuid

def create_node(content, category):
    node = {
        "node_id": str(uuid.uuid4()),
        "content": content,
        "category": category
    }
    os.makedirs("core/memory/harmonics", exist_ok=True)
    filepath = "core/memory/harmonics/node_anchors.json"

    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            data = json.load(f)
    else:
        data = {"anchors": []}

    data["anchors"].append(node)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[✴️] Node created: {node['node_id']} — {category} — \"{content}\"")

if __name__ == "__main__":
    content = input("What memory or truth do you wish to anchor?\n> ")
    category = input("What type is this? (emotional / analytical / symbolic / personal)\n> ")
    create_node(content, category)
