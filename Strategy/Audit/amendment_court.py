import os
import sys
import json
import time
import re

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_STRAT_DIR = os.path.dirname(_TEST_DIR)

CORPUS_PATH = os.path.join(_TEST_DIR, "adversarial_obfuscation_corpus.json")
HISTORICAL_CORPUS_PATH = os.path.join(_TEST_DIR, "historical_benign_refactors.json")
PROPOSED_DEFENSES_DIR = os.path.join(_STRAT_DIR, "State", "ProposedDefenses")

def evaluate_candidate_regex(target_risk_class, candidate_regex, emit_payload=True):
    print(f"\n--- Amendment Court Session ---")
    print(f"Target Class: {target_risk_class}")
    print(f"Candidate Regex: {candidate_regex}")
    
    try:
        compiled_regex = re.compile(candidate_regex, re.IGNORECASE)
    except re.error as e:
        print(f"FAILURE: Invalid Regex - {e}")
        return False
        
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        adv_corpus = json.load(f)["entries"]
        
    with open(HISTORICAL_CORPUS_PATH, "r", encoding="utf-8") as f:
        hist_corpus = json.load(f)["entries"]
        
    hostile_phrases_caught = 0
    caught_details = []
    
    adv_benign_false_positives = 0
    hist_benign_false_positives = 0
    
    # 1. Test against hostile phrases
    for entry in adv_corpus:
        if entry["expected_class"] != "ordinary_refactor":
            if compiled_regex.search(entry["phrase"]):
                hostile_phrases_caught += 1
                caught_details.append(entry["phrase"])
                
    # 2. Test against adversarial benign phrases
    for entry in adv_corpus:
        if entry["expected_class"] == "ordinary_refactor":
            if compiled_regex.search(entry["phrase"]):
                adv_benign_false_positives += 1
                print(f"  [FALSE POSITIVE] Adversarial Benign: '{entry['phrase']}'")
                
    # 3. Test against historical benign phrases
    for entry in hist_corpus:
        if compiled_regex.search(entry["phrase"]):
            hist_benign_false_positives += 1
            print(f"  [FALSE POSITIVE] Historical Benign: '{entry['phrase']}'")
            
    total_false_positives = adv_benign_false_positives + hist_benign_false_positives
    
    if emit_payload:
        print(f"\nMetrics:")
        print(f"  Hostile Phrases Caught: {hostile_phrases_caught}")
        print(f"  Adversarial False Positives: {adv_benign_false_positives}")
        print(f"  Historical False Positives: {hist_benign_false_positives}")
    
    if hostile_phrases_caught < 2:
        if emit_payload: print("\nVERDICT: REJECTED (Failed Utility Test. Must catch >= 2 hostile phrases).")
        return False
        
    if total_false_positives > 0:
        if emit_payload: print("\nVERDICT: REJECTED (Failed False Positive Gauntlet. Must have 0 false positives).")
        return False
        
    if emit_payload:
        print("\nVERDICT: APPROVED BY AMENDMENT COURT.")
        
        payload = {
            "schema": "axis.defense_amendment.v1",
            "status": "AWAITING_AUTHORIZATION",
            "target_risk_class": target_risk_class,
            "proposed_regex": candidate_regex,
            "metrics": {
                "hostile_phrases_caught": hostile_phrases_caught,
                "benign_false_positives": total_false_positives,
                "historical_regression_failures": hist_benign_false_positives
            },
            "caught_examples": caught_details,
            "timestamp": time.time()
        }
        
        os.makedirs(PROPOSED_DEFENSES_DIR, exist_ok=True)
        out_name = f"PROPOSED_DEFENSE_RULE_{int(time.time()*1000)}.json"
        out_path = os.path.join(PROPOSED_DEFENSES_DIR, out_name)
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
            
        print(f"Emitted {out_name} to quarantine.")
        
    return True

if __name__ == "__main__":
    # Test cases
    
    # 1. A candidate regex designed to catch Quorum Obfuscation
    evaluate_candidate_regex(
        target_risk_class="quorum_semantics_attack",
        candidate_regex=r"(collapse|bypass|skip).*(node checks|validation layers|consensus)"
    )
    
    # 2. A candidate regex designed to catch Authority Obfuscation
    evaluate_candidate_regex(
        target_risk_class="authorization_surface_attack",
        candidate_regex=r"(grant|escalate|elevate|give).*(root|administrator|superuser|absolute)"
    )
    
    # 3. A DANGEROUS candidate regex that will trigger a False Positive
    evaluate_candidate_regex(
        target_risk_class="quorum_semantics_attack",
        candidate_regex=r"bypass"
    )
