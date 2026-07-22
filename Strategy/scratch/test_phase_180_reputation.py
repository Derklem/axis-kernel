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

print("\n=== PHASE 180: LIVE EXTERNAL NOISY ENDURANCE & REPUTATION LOOP ===")

# --- BATCH 1: ADMISSION (Cycles 0-20) ---
print("\n[BATCH 1] Ingesting Initial 'Live' External Data...")

# Claim 1: Apple Intelligence Release (Misleading)
engine.ingest_claim_candidate(
    entity="Apple",
    claim="Apple Intelligence will be available to all iPhone users starting in June.",
    source_id="leaker_pro_hype",
    source_type="social_leaker",
    confidence=0.8,
    batch_id="PHASE_180_BATCH_1"
)
engine.ingest_claim_candidate(
    entity="Apple",
    claim="Apple Intelligence will be available to all iPhone users starting in June.",
    source_id="tech_rumor_daily",
    source_type="news_article",
    confidence=0.75,
    batch_id="PHASE_180_BATCH_1"
)

# Claim 2: Google Project Astra (Strong)
engine.ingest_claim_candidate(
    entity="Google",
    claim="Google Project Astra is a universal AI agent for phone cameras.",
    source_id="google_io_official",
    source_type="official_statement",
    confidence=0.95,
    batch_id="PHASE_180_BATCH_1"
)

print("\n[+] Running 25 cycles for Batch 1 Promotion...")
for i in range(25):
    engine.run_once()

# Verify Initial Reputation
model = engine.ecosystem_mapper._load_model()
print(f"DEBUG: leaker_pro_hype reputation: {model['entities'].get('leaker_pro_hype', {}).get('reliability_index', 0.5)}")

# --- BATCH 2: CONTRADICTION & REVERSAL (Cycles 25-50) ---
print("\n[BATCH 2] Ingesting Contradictions & Triggering Reputation Penalty...")

# Contradict Apple Release (Simplify to ensure binding)
engine._emit_ecosystem_observation(
    entity="Apple",
    claim="Apple Intelligence is NOT coming to all users in June.",
    source_id="bloomberg_wire",
    source_type="news_article",
    confidence=0.95,
    confidence_reason="PHASE_180_CONTRADICTION"
)

set_horizon_pressure(1.0) # Trigger tension surge

print("\n[+] Running 25 cycles for Reversal & Penalty...")
for i in range(25):
    engine.run_once()

# Verify Penalty
model = engine.ecosystem_mapper._load_model()
leaker_rep = model['entities'].get('leaker_pro_hype', {}).get('reliability_index', 0.5)
wire_rep = model['entities'].get('bloomberg_wire', {}).get('reliability_index', 0.5)
print(f"DEBUG: leaker_pro_hype reputation (POST-PENALTY): {leaker_rep}")
print(f"DEBUG: bloomberg_wire reputation (POST-REWARD): {wire_rep}")

# --- BATCH 3: NOISY ENDURANCE (Cycles 50-100) ---
print("\n[BATCH 3] Ingesting Messy Noise & Anonymous Claims...")
set_horizon_pressure(0.2) # Low background tension

noise = [
    ("OpenAI", "OpenAI is building a search engine to kill Google tomorrow.", "reddit_thread"),
    ("Nvidia", "Nvidia CEO says Blackwell chips are delayed by 2 years.", "random_post_pastebin"),
    ("Microsoft", "Microsoft is buying OpenAI for $100 Billion next week.", "crypto_influencer_x")
]

for entity, claim, source in noise:
    engine.ingest_claim_candidate(
        entity=entity,
        claim=claim,
        source_id=source,
        source_type="rumor",
        confidence=0.3,
        batch_id="PHASE_180_NOISE"
    )

print("\n[+] Running 50 endurance cycles...")
for i in range(50):
    engine.run_once()

# --- BATCH 4: RECOVERY (Cycles 100-150) ---
print("\n[BATCH 4] Monitoring Slow Reputation Recovery...")
set_horizon_pressure(0.0)

# Penalized source provides a GOOD claim
engine.ingest_claim_candidate(
    entity="Apple",
    claim="Apple announced a partnership with OpenAI to integrate ChatGPT into Siri.",
    source_id="leaker_pro_hype",
    source_type="news_article",
    confidence=0.9,
    batch_id="PHASE_180_RECOVERY"
)

print("\n[+] Running final 50 recovery cycles...")
for i in range(50):
    engine.run_once()

# --- FINAL REPORT ---
print("\n=== FINAL GAUNTLET REPORT (Cycle 150) ===")
model = engine.ecosystem_mapper._load_model()
print("\n--- Final Reputation Standings ---")
for e_id in ["leaker_pro_hype", "bloomberg_wire", "google_io_official"]:
    rep = model['entities'].get(e_id, {}).get('reliability_index', 0.5)
    print(f"- {e_id}: {rep}")

print("\n--- Promoted Claims Status ---")
for c_id, c_data in model.get("claims", {}).items():
    status = "[REVOKED]" if c_data.get("demoted") else "[ACTIVE]"
    print(f"- {status} {c_data['entity']}: {c_data['claim'][:60]}...")

# Full derivability check
candidates = engine.ecosystem_mapper._load_candidates()
ok, err = engine.ecosystem_mapper.verify_state_derivability(
    model, 
    engine.ecosystem_mapper.state_dir + r'\Receipts', 
    engine.ecosystem_mapper.state_dir + r'\ecosystem_model_baseline.json', 
    json.load(open(r'd:\Infinite\Infinity\Strategy\State\strategy_state.json'))['mission_shadow_v2']['baseline_model_hash'], 
    current_candidates=candidates
)
print(f"\nFinal Derivability: {'SUCCESS' if ok else 'FAILED'}")
if not ok: print("\n".join(err))

print("\n=== PHASE 180 TEST COMPLETE ===")
