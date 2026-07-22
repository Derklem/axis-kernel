import os, sys, json, time, subprocess
sys.path.append(r'd:\Infinite\Infinity\Strategy')
from strategy_engine import StrategyEngine

# Run super clean
subprocess.run([sys.executable, "super_clean.py"], check=True)

engine = StrategyEngine()

print("\n[1] Ingesting Initial Claims...")

# Claim A: Marketing Hype
engine.ingest_claim_candidate(
    entity="Meta",
    claim="Llama-4 will have AGI capabilities by next month.",
    source_id="meta_hype_blog",
    source_type="marketing_hype",
    confidence=0.5,
    batch_id="PHASE_177_TEST"
)

# Claim B: Rumor
engine.ingest_claim_candidate(
    entity="Anthropic",
    claim="Claude 4 is being delayed due to alignment failures.",
    source_id="reddit_user_99",
    source_type="rumor",
    confidence=0.5,
    batch_id="PHASE_177_TEST"
)

# Claim C: Real news
engine.ingest_claim_candidate(
    entity="Google",
    claim="Gemini 2.0 architecture details leaked.",
    source_id="tech_news_daily",
    source_type="news_article",
    confidence=0.8,
    batch_id="PHASE_177_TEST"
)

print("\n[2] Running initial 5 cycles...")
for i in range(5):
    engine.run_once()

print("\n[3] Injecting Agreement Signals at Cycle 5...")

# Claim A gets another weak marketing hype signal (Correlated Weak Sources)
engine.ingest_claim_candidate(
    entity="Meta",
    claim="Llama-4 will have AGI capabilities by next month.",
    source_id="hype_influencer_x",
    source_type="marketing_hype",
    confidence=0.6,
    batch_id="PHASE_177_TEST"
)

# Claim B gets a strong independent signal
engine.ingest_claim_candidate(
    entity="Anthropic",
    claim="Claude 4 is being delayed due to alignment failures.",
    source_id="independent_analyst_01",
    source_type="analyst_report",
    confidence=0.75,
    batch_id="PHASE_177_TEST"
)

# Claim C gets a correlated strong signal (same family)
engine.ingest_claim_candidate(
    entity="Google",
    claim="Gemini 2.0 architecture details leaked.",
    source_id="tech_news_weekly",
    source_type="news_article",
    confidence=0.8,
    batch_id="PHASE_177_TEST"
)

print("\n[4] Running cycles to reach Cycle 12 (Promotion Window)...")
for i in range(7):
    engine.run_once()

print("\n[5] Gauntlet Report (Cycle 12):")
candidates = engine.ecosystem_mapper._load_candidates()
print("\n--- Remaining Candidates in Pool ---")
for c_id, c_data in candidates.get("candidates", {}).items():
    print(f"- [{c_data['entity']}] {c_data['claim']}")
    print(f"  Survived: {c_data.get('cycles_survived', 0)} cycles | Agreement: {c_data.get('agreement_count', 1)}")

model = engine.ecosystem_mapper._load_model()
print("\n--- Promoted Claims in Ecosystem Model ---")
for c_id, c_data in model.get("claims", {}).items():
    print(f"- [PROMOTED] {c_data['entity']}: {c_data['claim']}")

print("\n[6] Running to Cycle 25 to test Chronic Failure Fracturing...")
for i in range(13):
    engine.run_once()

print("\n[7] Final Gauntlet Report (Cycle 25):")
candidates = engine.ecosystem_mapper._load_candidates()
print("\n--- Remaining Candidates in Pool ---")
for c_id, c_data in candidates.get("candidates", {}).items():
    print(f"- [{c_data['entity']}] {c_data['claim']}")
    print(f"  Survived: {c_data.get('cycles_survived', 0)} cycles | Agreement: {c_data.get('agreement_count', 1)}")

model = engine.ecosystem_mapper._load_model()
print("\n--- Promoted Claims in Ecosystem Model ---")
for c_id, c_data in model.get("claims", {}).items():
    print(f"- [PROMOTED] {c_data['entity']}: {c_data['claim']}")

print("\n=== PHASE 177 TEST COMPLETE ===")
