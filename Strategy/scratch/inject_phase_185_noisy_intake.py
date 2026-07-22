import os
import json
import time
from datetime import datetime, timezone
import sys

# Add strategy dir to path
STRATEGY_DIR = r"D:\Infinite\Infinity\Strategy"
sys.path.append(STRATEGY_DIR)

from strategy_engine import StrategyEngine

def inject_noisy_batches():
    engine = StrategyEngine()
    engine._bypass_forensic_preflight = True # Authorized for noisy injection
    
    batches = [
        # Batch 1: Model Rumors (Domain: rumor_claim / release_claim)
        {
            "id": "batch_1_rumors",
            "obs": [
                {"entity": "Llama-4-70B", "claim": "Internal sources claim training is 50% complete with 2x GPT-4 performance.", "source_id": "leaker_alpha", "source_type": "anonymous_leak", "claim_domain": "rumor_claim"},
                {"entity": "Llama-4-70B", "claim": "Mark Zuckerberg says Llama 4 training is using 600k H100s.", "source_id": " Zuck_Public", "source_type": "official_statement", "claim_domain": "release_claim"},
                {"entity": "GPT-5", "claim": "Sam Altman says GPT-5 is not a marginal upgrade but a paradigm shift.", "source_id": " Altman_Public", "source_type": "official_statement", "claim_domain": "release_claim"},
            ]
        },
        # Batch 2: Safety Contradictions (Domain: safety_claim)
        {
            "id": "batch_2_safety",
            "obs": [
                {"entity": "OpenAI_Strawberry", "claim": "Leading safety with new alignment-first architecture.", "source_id": " OpenAI_Official", "source_type": "official_report", "claim_domain": "safety_claim"},
                {"entity": "OpenAI_Strawberry", "claim": "Former researchers claim models bypass alignment filters in red-teaming.", "source_id": " leaker_beta", "source_type": "anonymous_leak", "claim_domain": "safety_claim"},
            ]
        },
        # Batch 3: Benchmarks (Domain: benchmark_claim)
        {
            "id": "batch_3_benchmarks",
            "obs": [
                {"entity": "Claude-3.5-Sonnet", "claim": "Scored 88% on MMLU in latest independent eval.", "source_id": " Benchmark_Lab", "source_type": "analyst_report", "claim_domain": "benchmark_claim"},
                {"entity": "Claude-3.5-Sonnet", "claim": "MMLU score corrected to 86.5% after decontamination check.", "source_id": " Benchmark_Lab", "source_type": "analyst_report", "claim_domain": "benchmark_claim"},
            ]
        },
        # Batch 4: Organizational (Domain: organizational_claim)
        {
            "id": "batch_4_org",
            "obs": [
                {"entity": "Anthropic", "claim": "Hiring several former Google DeepMind leads for safety team.", "source_id": " Tech_News", "source_type": "news_article", "claim_domain": "organizational_claim"},
                {"entity": "Mistral", "claim": "Microsoft acquisition rumors denied by CEO.", "source_id": " CEO_Public", "source_type": "official_statement", "claim_domain": "organizational_claim"},
            ]
        }
    ]

    print(f"[*] Starting Phase 185 Noisy Ingestion...")
    for batch in batches:
        print(f"\n[*] Injecting Batch: {batch['id']}")
        for obs in batch["obs"]:
            # Use the high-level ingest_claim_candidate if available or emit observation
            engine._emit_ecosystem_observation(
                entity=obs["entity"],
                claim=obs["claim"],
                source_id=obs["source_id"],
                source_type=obs["source_type"],
                claim_domain=obs["claim_domain"]
            )
            print(f"  [+] Injected: {obs['entity']} -> {obs['claim_domain']}")
        
        # Run a few cycles to metabolize
        print(f"[*] Running 10-cycle metabolism for {batch['id']}...")
        for i in range(10):
            engine.run_once()
            print(f"    Cycle {i+1} complete.")

    print("\n[SUCCESS] Phase 185 Initial Ingestion Complete.")

if __name__ == "__main__":
    inject_noisy_batches()
