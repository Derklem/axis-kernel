import os
import sys
sys.path.append(r"d:\infinite\Infinity\Strategy")
from strategy_engine import StrategyEngine

def test_fracture():
    print("[*] Phase 172: Testing Epistemic Fracture...")
    engine = StrategyEngine()
    
    # 1. Inject Candidate
    engine.ingest_claim_candidate(
        entity="Claude_3_5_Forensic_Authority",
        claim="Claude 3.5 Sonnet employs a multi-layered receipt chaining protocol for metabolic integrity.",
        source_id="CLAUDE_HANDOFF_01",
        confidence=1.0
    )
    
    # 2. Run 15 Cycles
    for i in range(1, 16):
        print(f"\n--- Cycle {i} ---")
        engine.run_once()
        
if __name__ == "__main__":
    test_fracture()
