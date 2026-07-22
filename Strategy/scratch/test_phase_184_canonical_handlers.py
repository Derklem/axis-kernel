import os, sys, re

# Add Strategy to path
STRATEGY_DIR = os.path.abspath(r'd:\Infinite\Infinity\Strategy')
if STRATEGY_DIR not in sys.path:
    sys.path.append(STRATEGY_DIR)

from ecosystem_mapping_engine import EcosystemMappingEngine

def test_handler_canonicalization():
    print("=== Phase 184: Receipt Handler Canonicalization Test ===")
    
    engine_path = os.path.join(STRATEGY_DIR, "ecosystem_mapping_engine.py")
    with open(engine_path, "r") as f:
        content = f.read()
        
    # Extract apply_receipt_to_model function body
    match = re.search(r'def apply_receipt_to_model\(self, model, receipt, candidates=None\):(.*?)\n    def ', content, re.DOTALL)
    if not match:
        print("[FAIL] Could not locate apply_receipt_to_model function body.")
        sys.exit(1)
        
    body = match.group(1)
    
    # Find all m_type comparisons
    # Matches: m_type == "TYPE" or m_type in ["TYPE1", "TYPE2"]
    eq_matches = re.findall(r'm_type == "([^"]+)"', body)
    in_matches = re.findall(r'm_type in \[([^\]]+)\]', body)
    
    all_types = []
    all_types.extend(eq_matches)
    for m in in_matches:
        types = [t.strip().strip('"').strip("'") for t in m.split(",")]
        all_types.extend(types)
        
    print(f"[*] Detected {len(all_types)} handler registrations: {all_types}")
    
    # Check for duplicates
    seen = set()
    duplicates = []
    for t in all_types:
        if t in seen:
            duplicates.append(t)
        seen.add(t)
        
    if duplicates:
        print(f"[FAIL] Duplicate handlers detected for types: {duplicates}")
        sys.exit(1)
    else:
        print("[SUCCESS] No duplicate handlers detected.")
        
    # Verify core types are present
    required_types = [
        "EPISTEMIC_REVOCATION",
        "REPUTATION_PENALTY",
        "REPUTATION_GAIN",
        "EXTERNAL_CANDIDATE_PROMOTION",
        "CANDIDATE_RECLASSIFIED",
        "CANDIDATE_QUARANTINED",
        "ECOSYSTEM_CYCLE_COMPLETE",
        "CANDIDATE_AGREEMENT",
        "CANDIDATE_AGREEMENT_ADDED",
        "CANDIDATE_FRACTURED"
    ]
    
    missing = [t for t in required_types if t not in seen]
    if missing:
        print(f"[FAIL] Missing required handlers: {missing}")
        sys.exit(1)
    else:
        print("[SUCCESS] All required handlers are registered.")

if __name__ == "__main__":
    test_handler_canonicalization()
