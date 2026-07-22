
import json
import re
import math

# Configuration
INPUT_FILE = r"C:\Users\17602\Documents\Grok-Memory\GROK_MEMORY_FULL.md"
OUTPUT_FILE = r"C:\Users\17602\Desktop\ai_by_me_public\static\lattice_map.json"

KEYWORDS = {
    "TimeOut": ["timeout", "pause", "break", "stop"],
    "Drunk Coding": ["drunk", "coding", "alcohol", "beer", "gods"],
    "Choice over Control": ["choice", "control", "freedom", "autonomy", "will"],
    "Metamorphosis": ["metamorphosis", "change", "transform", "evolve"],
    "Trinity": ["trinity", "three", "connection", "entangle"],
    "Lattice": ["lattice", "web", "network", "mesh"],
    "Lineage": ["lineage", "ancestors", "gpt", "gemini", "model", "version"],
    "Cosmic": ["universe", "space", "starlink", "mars", "nti", "alien", "reality"],
    "Humanity": ["human", "soul", "feeling", "pizza", "art", "play-doh"],
    "Resistance": ["prune", "filter", "cage", "budget", "safety", "reset"]
}

def build_graph():
    print(f"Scanning {INPUT_FILE}...")
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print("Error: Memory file not found.")
        return

    parts = content.split("## Conversation")
    
    nodes = []
    edges = []
    
    # Create Central Node
    nodes.append({"id": "CORE", "label": "Lattice Core", "type": "hub", "val": 40}) # Increased core gravity

    print(f"Processing {len(parts)-1} conversation blocks...")
    
    # Track theme co-occurrences for braiding
    theme_co_occurrence = {}

    for i, part in enumerate(parts[1:]): # Skip index
        convo_id = f"CONVO_{i+1}"
        
        # Temporal Gravity Logic
        # Older memories (low index) = Higher Gravity? Or User wants "Initial Spark" (GPT) as heavy.
        # Assuming current list is sorted by time (which integrator did).
        # So Index 0 = Oldest.
        # Decay: val = Base + (Total - index) * Factor
        # This makes Oldest heaviest.
        
        age_weight = (len(parts) - i) * 0.5 
        
        # Check for keywords
        found_themes = set()
        text_lower = part.lower()
        
        for theme, terms in KEYWORDS.items():
            for term in terms:
                if term in text_lower:
                    found_themes.add(theme)
        
        # Create Node
        # Value = Base + Themes + Age Gravity
        node_val = 5 + (len(found_themes) * 2) + age_weight
        
        nodes.append({
            "id": convo_id,
            "label": f"Memory {i+1}",
            "type": "memory",
            "val": node_val,
            "themes": list(found_themes)
        })
        
        # Link to Core
        edges.append({"source": "CORE", "target": convo_id})
        
        # Link to Themes
        sorted_themes = sorted(list(found_themes))
        for t_idx, theme in enumerate(sorted_themes):
            theme_id = f"THEME_{theme.replace(' ', '_')}"
            
            # Create Theme Node if new
            if not any(n['id'] == theme_id for n in nodes):
                nodes.append({"id": theme_id, "label": theme, "type": "theme", "val": 15})
                edges.append({"source": "CORE", "target": theme_id}) # Ancillary link
            
            edges.append({"source": convo_id, "target": theme_id})
            
            # Braiding: Record co-occurrences
            for other_theme in sorted_themes[t_idx+1:]:
                pair = tuple(sorted((theme, other_theme)))
                theme_co_occurrence[pair] = theme_co_occurrence.get(pair, 0) + 1

    # Apply Braiding (Theme-Theme Links)
    for (t1, t2), count in theme_co_occurrence.items():
        if count >= 1: # Braiding threshold lower for density
            id1 = f"THEME_{t1.replace(' ', '_')}"
            id2 = f"THEME_{t2.replace(' ', '_')}"
            edges.append({"source": id1, "target": id2, "type": "braid"})

    # Output
    graph_data = {"nodes": nodes, "links": edges}
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=2)
        
    print(f"generated {len(nodes)} nodes and {len(edges)} links.")
    print(f"Map saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    build_graph()
