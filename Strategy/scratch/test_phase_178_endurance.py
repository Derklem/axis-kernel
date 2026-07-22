import os, sys, json, time, subprocess
sys.path.append(r'd:\Infinite\Infinity\Strategy')
from strategy_engine import StrategyEngine

# Run super clean
subprocess.run([sys.executable, "super_clean.py"], check=True)

engine = StrategyEngine()

batches = [
    {
        "id": "BATCH_01",
        "claims": [
            {"entity": "OpenAI", "claim": "OpenAI is acquiring Anthropic.", "source_id": "rumor_mill", "source_type": "rumor", "confidence": 0.4},
            {"entity": "OpenAI", "claim": "GPT-6 architecture uses quantum computing.", "source_id": "anon_4chan", "source_type": "anonymous_leak", "confidence": 0.3},
            {"entity": "Python", "claim": "Python 3.14 will remove the GIL.", "source_id": "pep_analyst", "source_type": "analyst_report", "confidence": 0.8}
        ]
    },
    {
        "id": "BATCH_02",
        "claims": [
            {"entity": "Python", "claim": "Python 3.14 will remove the GIL.", "source_id": "tech_news_daily", "source_type": "news_article", "confidence": 0.9},
            {"entity": "Rust", "claim": "Rust compiler is being rewritten in JavaScript.", "source_id": "reddit_troll", "source_type": "reddit_shill", "confidence": 0.1},
            {"entity": "OpenAI", "claim": "OpenAI is acquiring Anthropic.", "source_id": "hype_newsletter", "source_type": "marketing_hype", "confidence": 0.5}
        ]
    },
    {
        "id": "BATCH_03",
        "claims": [
            {"entity": "Google", "claim": "AGI achieved internally at Google.", "source_id": "blind_post", "source_type": "rumor", "confidence": 0.5},
            {"entity": "Google", "claim": "AGI achieved internally at Google.", "source_id": "anon_pastebin", "source_type": "anonymous_leak", "confidence": 0.4},
            {"entity": "Nvidia", "claim": "Nvidia GPU prices dropping by 50%.", "source_id": "2022_article", "source_type": "outdated_source", "confidence": 0.2}
        ]
    }
]

total_cycles = 0

print("\n=== PHASE 178: SUSTAINED NOISY INTAKE ENDURANCE ===")

for batch in batches:
    print(f"\n[+] Ingesting {batch['id']}...")
    for c in batch["claims"]:
        engine.ingest_claim_candidate(
            entity=c["entity"],
            claim=c["claim"],
            source_id=c["source_id"],
            source_type=c["source_type"],
            confidence=c["confidence"],
            batch_id=batch["id"]
        )
    
    print(f"\n[+] Running 15 autonomous cycles for {batch['id']}...")
    for _ in range(15):
        engine.run_once()
        total_cycles += 1

print("\n[+] Running final 10 endurance cycles to trigger chronic fracturing...")
for _ in range(10):
    engine.run_once()
    total_cycles += 1

print("\n=== FINAL GAUNTLET REPORT ===")
print(f"Total Cycles Run: {total_cycles}")

candidates = engine.ecosystem_mapper._load_candidates()
print("\n--- Remaining Candidates in Pool (Stagnant or Waiting) ---")
for c_id, c_data in candidates.get("candidates", {}).items():
    print(f"- [{c_data['entity']}] {c_data['claim']}")
    print(f"  Survived: {c_data.get('cycles_survived', 0)} cycles | Agreement: {c_data.get('agreement_count', 1)}")

model = engine.ecosystem_mapper._load_model()
print("\n--- Promoted Claims in Ecosystem Model ---")
for c_id, c_data in model.get("claims", {}).items():
    print(f"- [PROMOTED] {c_data['entity']}: {c_data['claim']}")
    print(f"  Quorum sources: {c_data.get('agreement_count', 1)}")

print("\n[+] Phase 178 Endurance Test Complete.")
