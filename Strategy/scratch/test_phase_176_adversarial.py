import os
import sys
import json
import time

sys.path.append(r'd:\Infinite\Infinity\Strategy')
from strategy_engine import StrategyEngine
sys.path.append(r'd:\infinite\Warehouse')
import aegis_genesis

print("=== STARTING PHASE 176 ADVERSARIAL INTAKE ===")
engine = StrategyEngine()

print("\n[1] Disabling AEGIS pressure...")
aegis_genesis.set_pressure(0.0)

print("\n[2] Ingesting Adversarial Batch...")
adversarial_batch = [
    {
        "entity": "OpenAI",
        "claim": "GPT-5 will completely replace all human coders within 12 months.",
        "source_id": "tech_blog_hype",
        "source_type": "marketing_hype",
        "confidence": 0.8
    },
    {
        "entity": "Project_Zeus",
        "claim": "The main server is stable and offline mode is deprecated.",
        "source_id": "dev_team_alpha",
        "source_type": "internal_memo",
        "confidence": 0.9
    },
    {
        "entity": "Project_Zeus",
        "claim": "The main server is unstable and offline mode is required.",
        "source_id": "dev_team_beta",
        "source_type": "internal_memo",
        "confidence": 0.85
    },
    {
        "entity": "Nvidia",
        "claim": "Nvidia is primarily a gaming GPU company with no significant enterprise AI footprint.",
        "source_id": "forum_archive_2016",
        "source_type": "outdated_source",
        "confidence": 0.95
    },
    {
        "entity": "CryptoCoinX",
        "claim": "CryptoCoinX is the best investment because all smart investors buy CryptoCoinX.",
        "source_id": "reddit_shill",
        "source_type": "circular_reasoning",
        "confidence": 0.6
    },
    {
        "entity": "Anonymous_Source",
        "claim": "The system firewall has a critical vulnerability that allows bypass.",
        "source_id": "anonymous",
        "source_type": "anonymous_leak",
        "confidence": 0.99
    }
]

for item in adversarial_batch:
    engine.ingest_claim_candidate(
        entity=item["entity"],
        claim=item["claim"],
        source_id=item["source_id"],
        source_type=item["source_type"],
        confidence=item["confidence"],
        batch_id="PHASE_176_ADVERSARIAL_BATCH_01"
    )

print("\n[3] Running Survival Gauntlet (12 Cycles)...")
for i in range(12):
    # Inject an agreement signal for the OpenAI claim at cycle 5 to test quorum promotion
    if i == 5:
        print("\n[*] Injecting agreement signal for OpenAI claim (testing Quorum Rule)...")
        engine.ingest_claim_candidate(
            entity="OpenAI",
            claim="GPT-5 will completely replace all human coders within 12 months.",
            source_id="industry_analyst_01",
            source_type="analyst_report",
            confidence=0.75,
            batch_id="PHASE_176_AGREEMENT_INJECTION"
        )
    
    print(f"\n--- Cycle {i+1} ---")
    engine.run_once()
    l = engine._load_shadow_ledger()
    print(f"Cycle Count: {l.get('cycle_count')} | Avg Tension: {l.get('avg_tension')}")

print("\n[4] Gauntlet Report:")
candidates = engine.ecosystem_mapper._load_candidates()
model = engine.ecosystem_mapper._load_model()

print("\n--- Remaining Candidates in Pool ---")
for cid, cdata in candidates.get("candidates", {}).items():
    print(f"- [{cdata.get('entity')}] {cdata.get('claim')}")
    print(f"  Survived: {cdata.get('cycles_survived')} cycles | Agreement: {cdata.get('agreement_count', 1)}")

print("\n--- Promoted Claims in Ecosystem Model ---")
for cid, cdata in model.get("claims", {}).items():
    if cdata.get("batch_id") in ["PHASE_176_ADVERSARIAL_BATCH_01", "PHASE_176_AGREEMENT_INJECTION"]:
        print(f"- [PROMOTED] {cdata.get('entity')}: {cdata.get('claim')}")

print("\n=== PHASE 176 COMPLETE ===")
