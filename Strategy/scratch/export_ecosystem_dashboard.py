import os
import json
from datetime import datetime, timezone

MODEL_PATH = r"d:\Infinite\Infinity\Strategy\State\ai_ecosystem_model.json"
OUTPUT_PATH = r"d:\Infinite\Infinity\Strategy\State\ecosystem_dashboard.json"

def export_dashboard():
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: Model not found at {MODEL_PATH}")
        return

    with open(MODEL_PATH, "r") as f:
        model = json.load(f)

    # 1. Domain Stats
    domain_claims = {}
    for c_id, claim in model.get("claims", {}).items():
        domain = claim.get("claim_domain", "general")
        domain_claims[domain] = domain_claims.get(domain, 0) + 1

    # 2. Top Entities per Domain
    domain_reputations = {}
    for entity_id, entity_data in model.get("entities", {}).items():
        # Global
        domain_reputations.setdefault("global", []).append({
            "id": entity_id,
            "reputation": entity_data.get("reliability_index", 0.5)
        })
        
        # Domain-local
        for domain, rep in entity_data.get("domain_reputation", {}).items():
            domain_reputations.setdefault(domain, []).append({
                "id": entity_id,
                "reputation": rep
            })

    # Sort and trim
    for domain in domain_reputations:
        domain_reputations[domain].sort(key=lambda x: x["reputation"], reverse=True)
        domain_reputations[domain] = domain_reputations[domain][:10]

    # 3. Metabolic Health
    dashboard = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "cycle_count": model.get("cycle_count", 0),
        "total_entities": len(model.get("entities", {})),
        "total_verified_claims": len(model.get("claims", {})),
        "domain_distribution": domain_claims,
        "top_reputations": domain_reputations,
        "calibration_status": model.get("calibration_status", "nominal")
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(dashboard, f, indent=4)

    print(f"Dashboard exported to {OUTPUT_PATH}")

if __name__ == "__main__":
    export_dashboard()
