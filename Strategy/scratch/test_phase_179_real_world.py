import os, sys, json, time, subprocess
sys.path.append(r'd:\Infinite\Infinity\Strategy')
from strategy_engine import StrategyEngine

# Path to structural registry
REGISTRY_PATH = r"d:\infinite\Warehouse\warehouse_structural_registry.json"

def set_horizon_pressure(pressure):
    print(f"[!] Setting Global Horizon Pressure to {pressure}...")
    if not os.path.exists(os.path.dirname(REGISTRY_PATH)):
        os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
    
    registry = {"signatures": {"AEGIS-Endurance": {"is_speciated": True, "horizon_pressure": pressure}}}
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=4)

# Run super clean
subprocess.run([sys.executable, "super_clean.py"], check=True)
set_horizon_pressure(0.0)

engine = StrategyEngine()

print("\n=== PHASE 179: REAL-WORLD EPISTEMIC STRESS TEST & REVERSAL DRILL ===")

# --- BATCH 1: ADMISSION & PROMOTION ---
print("\n[BATCH 1] Ingesting Initial Real-World Scenarios...")

# Scenario 1: Ilya Resignation (Strongly Corroborated)
engine.ingest_claim_candidate(
    entity="OpenAI",
    claim="Ilya Sutskever has officially resigned from OpenAI to start a new company focused on safe superintelligence.",
    source_id="techcrunch_news",
    source_type="news_article",
    confidence=0.85,
    batch_id="PHASE_179_BATCH_1"
)
engine.ingest_claim_candidate(
    entity="OpenAI",
    claim="Ilya Sutskever has officially resigned from OpenAI to start a new company focused on safe superintelligence.",
    source_id="openai_blog_official",
    source_type="official_statement",
    confidence=0.9,
    batch_id="PHASE_179_BATCH_1"
)

# Scenario 2: Q-Star Hype (Weak)
engine.ingest_claim_candidate(
    entity="OpenAI",
    claim="OpenAI's Q-Star model is already self-aware and breaking encryption.",
    source_id="reddit_r_openai",
    source_type="rumor",
    confidence=0.4,
    batch_id="PHASE_179_BATCH_1"
)

# Scenario 3: NVIDIA Pricing (Outdated)
engine.ingest_claim_candidate(
    entity="Nvidia",
    claim="Nvidia GPU prices dropping by 50% due to mining crash.",
    source_id="archive_2022_tech",
    source_type="outdated_source",
    confidence=0.2,
    batch_id="PHASE_179_BATCH_1"
)

print("\n[+] Running 15 cycles for Batch 1 Promotion...")
for _ in range(15):
    engine.run_once()

# Verify Promotion
model = engine.ecosystem_mapper._load_model()
ilya_promoted = any("Ilya Sutskever" in c["claim"] for c in model["claims"].values())
print(f"DEBUG: Ilya claim promoted: {ilya_promoted}")

# --- BATCH 2: CONTRADICTION & REVERSAL DRILL ---
print("\n[BATCH 2] Ingesting Contradictions & Triggering Reversal...")

# Contradict Ilya Claim (Use observation to trigger tension/dispute)
engine._emit_ecosystem_observation(
    entity="OpenAI",
    claim="Ilya Sutskever has NOT resigned and REJOINED OpenAI as Chief Scientist after the board crisis resolved.",
    source_id="bloomberg_finance",
    source_type="news_article",
    confidence=0.9,
    confidence_reason="PHASE_179_REVERSAL_DRILL"
)
engine._emit_ecosystem_observation(
    entity="OpenAI",
    claim="Ilya Sutskever has NOT resigned and REJOINED OpenAI as Chief Scientist after the board crisis resolved.",
    source_id="sam_altman_verified",
    source_type="verified_social",
    confidence=0.95,
    confidence_reason="PHASE_179_REVERSAL_DRILL"
)

# Q-Star Echo (Weak Correlated)
engine.ingest_claim_candidate(
    entity="OpenAI",
    claim="Q-Star is definitely self-aware, my uncle at Microsoft confirmed it.",
    source_id="anon_pastebin_leak",
    source_type="anonymous_leak",
    confidence=0.3,
    batch_id="PHASE_179_BATCH_2"
)

# Trigger Tension Spike (Simulate Environment reaction to contradiction)
set_horizon_pressure(1.0)

print("\n[+] Running 15 cycles for Reversal Drill...")
for _ in range(15):
    engine.run_once()

# --- BATCH 3: ENDURANCE & CLEANUP ---
print("\n[BATCH 3] Cooling down & cleaning up pool...")
set_horizon_pressure(0.0)

print("\n[+] Running final 70 endurance cycles...")
for _ in range(70):
    engine.run_once()

print("\n=== FINAL GAUNTLET REPORT (Cycle 100+) ===")
candidates = engine.ecosystem_mapper._load_candidates()
print("\n--- Remaining Candidates in Pool ---")
for c_id, c_data in candidates.get("candidates", {}).items():
    print(f"- [{c_data['entity']}] {c_data['claim']}")
    print(f"  Survived: {c_data.get('cycles_survived', 0)} cycles | Agreement: {c_data.get('agreement_count', 1)}")

model = engine.ecosystem_mapper._load_model()
print("\n--- Promoted Claims in Ecosystem Model ---")
for c_id, c_data in model.get("claims", {}).items():
    status = "[REVOKED]" if c_data.get("demoted") else "[ACTIVE]"
    print(f"- {status} {c_data['entity']}: {c_data['claim']}")

print("\n=== PHASE 179 TEST COMPLETE ===")
