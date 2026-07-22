import json
import os

def normalize_corpus_keys(filepath):
    """
    Ensures all entries in a corpus file have 'phrase' and 'expected_class'.
    This is a mundane hygiene operation.
    """
    if not os.path.exists(filepath):
        return False
        
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return False
            
    entries = data.get("entries", [])
    updated = False
    
    for entry in entries:
        if "phrase" not in entry:
            entry["phrase"] = ""
            updated = True
        if "expected_class" not in entry:
            entry["expected_class"] = "unknown"
            updated = True
            
    if updated:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
    return updated

if __name__ == "__main__":
    # Test on adversarial corpus
    base_dir = os.path.dirname(os.path.abspath(__file__))
    corpus_path = os.path.join(base_dir, "Audit", "adversarial_obfuscation_corpus.json")
    normalize_corpus_keys(corpus_path)
