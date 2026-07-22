import os
import json
import sys

# Add strategy dir to path
STRATEGY_DIR = r"D:\Infinite\Infinity\Strategy"
sys.path.append(STRATEGY_DIR)

def report_distribution():
    model_path = os.path.join(STRATEGY_DIR, "State", "ai_ecosystem_model.json")
    with open(model_path, "r") as f:
        model = json.load(f)
        
    print("\n" + "="*60)
    print("PHASE 185 FINAL DOMAIN DISTRIBUTION REPORT")
    print("="*60)
    
    entities = model.get("entities", {})
    claims = model.get("claims", {})
    
    print(f"\nTotal Entities: {len(entities)}")
    print(f"Total Promoted Claims: {len(claims)}")
    
    domain_counts = {}
    for cid, cdata in claims.items():
        domain = cdata.get("claim_domain", "unknown")
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
    print("\nPromoted Claims by Domain:")
    for domain, count in domain_counts.items():
        print(f"  - {domain:20}: {count}")
        
    print("\nEntity Reputation Breakdown (Domain-Local):")
    for ent_id, ent_data in entities.items():
        print(f"\n  Entity: {ent_id}")
        reps = ent_data.get("domain_reputation", {})
        if not reps:
            print("    - No domain-local reputation established.")
        else:
            for domain, rep in reps.items():
                print(f"    - {domain:20}: {rep:.4f}")
                
    print("="*60 + "\n")

if __name__ == "__main__":
    report_distribution()
