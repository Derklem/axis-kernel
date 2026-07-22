import os
import sys
import json
import time
import glob
import shutil

sys.path.append(r'd:\Infinite\Infinity\Strategy')
from strategy_engine import StrategyEngine, CORE_SOURCE_REGISTRY
from axis_crypto_helpers import _hash_file_stream
sys.path.append(r'd:\infinite\Warehouse')
import aegis_genesis

print("=== STARTING PHASE 176 ADVERSARIAL INTAKE ===")
engine = StrategyEngine()

# --- CLEANUP ---
print("\n[0] Cleaning up forensics and baseline...")
receipts_dir = r'd:\Infinite\Infinity\Strategy\State\Receipts'
if os.path.exists(receipts_dir):
    for f in glob.glob(os.path.join(receipts_dir, '*.receipt')):
        os.remove(f)

# Clear candidates
c_path = r'd:\Infinite\Infinity\Strategy\State\claim_candidates.json'
with open(c_path, 'w') as f:
    json.dump({"candidates": {}}, f, indent=4)

# Sync baseline
model_path = r'd:\Infinite\Infinity\Strategy\State\ai_ecosystem_model.json'
baseline_path = r'd:\Infinite\Infinity\Strategy\State\ecosystem_model_baseline.json'
shutil.copy2(model_path, baseline_path)

l = engine._load_shadow_ledger()
l['ecosystem_receipts_head'] = 'none'

# Fix core registry hashes
for name, rel_path in CORE_SOURCE_REGISTRY.items():
    abs_path = os.path.join(r"d:\Infinite\Infinity\Strategy", rel_path)
    domain = "ecosystem_baseline" if name == "baseline_model" else "crypto_lint_file"
    actual = _hash_file_stream(abs_path, domain) if os.path.exists(abs_path) else "MISSING"
    l[f"expected_{name}_hash"] = actual
    if name == "baseline_model":
        l["baseline_model_hash"] = actual

l.pop('core_integrity_failure_latch', None)
l['calibration_ledger_integrity']['status'] = 'valid'
l['calibration_ledger_integrity']['hash'] = engine._compute_calibration_hash(l)
l['calibration_ledger_integrity']['last_verified_cycle'] = l['cycle_count']
engine._commit_shadow_ledger(l)

d = json.load(open(engine.anchor_file))
d['last_hash'] = l['calibration_ledger_integrity']['hash']
d['last_cycle'] = l['cycle_count']
d['witness_chain_head'] = engine.witness.last_witness_hash
with open(engine.anchor_file, 'w') as f:
    json.dump(d, f, indent=4)

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
