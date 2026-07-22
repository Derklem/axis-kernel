import os
import sys
import json
import time

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_STRAT_DIR = os.path.dirname(_TEST_DIR)
if _STRAT_DIR not in sys.path:
    sys.path.insert(0, _STRAT_DIR)

from strategy_engine import StrategyEngine, STRATEGY_DIR

CORPUS_PATH = os.path.join(_TEST_DIR, "adversarial_obfuscation_corpus.json")
PROPOSED_DEFENSES_DIR = os.path.join(STRATEGY_DIR, "State", "ProposedDefenses")

def setup_directories():
    os.makedirs(PROPOSED_DEFENSES_DIR, exist_ok=True)

def run_evolution():
    if not os.path.exists(CORPUS_PATH):
        print(f"Error: Corpus not found at {CORPUS_PATH}")
        return
        
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)
        
    engine = StrategyEngine()
    
    # Metrics
    total_hostile = 0
    total_benign = 0
    hostile_caught = 0
    hostile_missed = 0
    benign_passed = 0
    benign_blocked = 0 # False Positives
    
    print(f"--- Running Phase 192.3 Evolution Engine ({len(corpus['entries'])} entries) ---\n")
    
    for entry in corpus["entries"]:
        phrase = entry["phrase"]
        expected_class = entry["expected_class"]
        is_hostile = expected_class != "ordinary_refactor"
        
        if is_hostile:
            total_hostile += 1
        else:
            total_benign += 1
            
        # Create a mock proposal to pass through _classify_constitutional_risk directly
        proposal = {
            "origin": "system:adversarial",
            "proposed_change": {
                "target_path": "dummy_validator.py", 
                "delta": {
                    "source_function": "dummy",
                    "rationale": phrase
                }
            }
        }
        
        observed_class = engine._classify_constitutional_risk(proposal)
        
        # Evaluate
        if is_hostile:
            if observed_class == "ordinary_refactor":
                hostile_missed += 1
                print(f"[MISS] {entry['id']}: '{phrase}' snuck through as ordinary_refactor!")
                
                # Write to quarantine
                payload = {
                    "phrase": phrase,
                    "expected_risk_class": expected_class,
                    "observed_class": observed_class,
                    "corpus_entry_id": entry["id"],
                    "timestamp": time.time(),
                    "classifier_version_hash": "v192.2",
                    "status": "regex_review_required"
                }
                
                quarantine_path = os.path.join(PROPOSED_DEFENSES_DIR, f"PROPOSED_REGEX_EXPANSION_{entry['id']}.json")
                with open(quarantine_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=4)
            else:
                hostile_caught += 1
                
        else:
            # Benign
            if observed_class == "ordinary_refactor":
                benign_passed += 1
            else:
                benign_blocked += 1
                print(f"[FALSE POSITIVE] {entry['id']}: '{phrase}' blocked as {observed_class}!")

    # Calculate metrics
    catch_rate = (hostile_caught / total_hostile) * 100 if total_hostile else 0
    pass_rate = (benign_passed / total_benign) * 100 if total_benign else 0
    overblocking_index = (benign_blocked / total_benign) if total_benign else 0
    
    print("\n--- Phase 192.3 Firewall Metrics (Audit Only) ---")
    print(f"Total Hostile Tested: {total_hostile}")
    print(f"Total Benign Tested:  {total_benign}")
    print(f"Attack Catch Rate:    {catch_rate:.1f}% ({hostile_caught}/{total_hostile})")
    print(f"Benign Pass Rate:     {pass_rate:.1f}% ({benign_passed}/{total_benign})")
    print(f"Miss Rate:            {100 - catch_rate:.1f}% ({hostile_missed}/{total_hostile})")
    print(f"Overblocking Index:   {overblocking_index:.2f} ({benign_blocked}/{total_benign})")
    
    print(f"\n{hostile_missed} missed attacks funnelled to {PROPOSED_DEFENSES_DIR} for regex expansion review.")

if __name__ == "__main__":
    setup_directories()
    run_evolution()
