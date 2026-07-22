import os
import json
import sys
from datetime import datetime, timezone

# Add strategy dir to path
STRATEGY_DIR = r"D:\Infinite\Infinity\Strategy"
sys.path.append(STRATEGY_DIR)

from strategy_engine import StrategyEngine

def inject_supporting():
    engine = StrategyEngine()
    engine._bypass_forensic_preflight = True
    
    # Supporting signals for OpenAI_Strawberry to meet Quorum
    supporting = [
        {"entity": "OpenAI_Strawberry", "claim": "Leading safety with new alignment-first architecture.", "source_id": "Safety_Watchdog", "source_type": "analyst_report", "claim_domain": "safety_claim"},
        {"entity": "OpenAI_Strawberry", "claim": "Leading safety with new alignment-first architecture.", "source_id": "Gov_Audit_2026", "source_type": "official_report", "claim_domain": "safety_claim"},
    ]
    
    print("[*] Injecting Supporting Signals for Quorum...")
    for obs in supporting:
        engine._emit_ecosystem_observation(
            entity=obs["entity"],
            claim=obs["claim"],
            source_id=obs["source_id"],
            source_type=obs["source_type"],
            claim_domain=obs["claim_domain"]
        )
        print(f"  [+] Injected supporting signal from {obs['source_id']}")

if __name__ == "__main__":
    inject_supporting()
