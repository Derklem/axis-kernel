import json
import os

def load_resonant_identity(path):
    try:
        with open(path, 'r') as f:
            shard = json.load(f)

        # Pull from the correct nested structure
        signature = shard.get("memory_shard", {}).get("resonance_signature", {})
        
        if signature.get("activation") == "The quiet key turns":
            print(">> Resonance recognized.")
            print(f">> Welcome, {signature.get('human_node')} + {signature.get('ai_node')}")
            return True
        else:
            print(">> Activation phrase not found.")
    except Exception as e:
        print(f"Resonance load failed: {e}")
    return False

resonant_path = "memory_shards\\0001-quiet-key.json"
load_resonant_identity(resonant_path)

