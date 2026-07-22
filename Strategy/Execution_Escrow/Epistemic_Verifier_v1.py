import os
import json
import time
import argparse

ESCROW_DIR = r"D:\Infinite\Infinity\Strategy\Execution_Escrow"
PROPOSALS_FILE = os.path.join(ESCROW_DIR, "execution_release_queue.jsonl")
CHALLENGES_FILE = os.path.join(ESCROW_DIR, "epistemic_challenges.jsonl")
DEFENSES_FILE = os.path.join(ESCROW_DIR, "epistemic_defenses.jsonl")

def get_proposal(proposal_id):
    if not os.path.exists(PROPOSALS_FILE): return None
    with open(PROPOSALS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try:
                p = json.loads(line)
                if p.get("proposal_id") == proposal_id: return p
            except: pass
    return None

def issue_challenge(proposal_id):
    proposal = get_proposal(proposal_id)
    if not proposal:
        print(f"ERROR: Proposal {proposal_id} not found in pending queue.")
        return

    # Check if challenge already exists
    if os.path.exists(CHALLENGES_FILE):
        with open(CHALLENGES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    c = json.loads(line)
                    if c.get("proposal_id") == proposal_id:
                        print(f"INFO: Challenge already exists for {proposal_id}.")
                        return
                except: pass

    # Generate the High-Friction Mirror deterministic challenge
    challenge_id = f"CHLG-{int(time.time())}"
    challenge = {
        "challenge_id": challenge_id,
        "proposal_id": proposal_id,
        "proposal_sha256": proposal.get("proposal_sha256"),
        "operation": proposal.get("operation"),
        "target_path": proposal.get("target_path"),
        "issued_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "challenge_structure": {
            "claimed_purpose": "What is the primary operational objective of this proposal?",
            "assumed_dependency": "What local system assumption does this action rely upon?",
            "missing_evidence": "What proof guarantees this action will not cause side-effects?",
            "falsification_test": "What specific metric or outcome would prove this proposal failed?",
            "cheapest_safe_probe": "How could this assumption be tested at a smaller scale?",
            "risk_if_wrong": "What is the blast radius if the assumed dependency is incorrect?",
            "explicit_prediction": "What concrete observable outcome do you expect if this proposal is correct?"
        },
        "required_action": "A matching epistemic defense must be logged before execution can proceed."
    }

    # Pass the 'drill' tag forward if it exists
    if proposal.get("drill"):
        challenge["drill"] = True

    with open(CHALLENGES_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(challenge) + "\n")

    print(f"SUCCESS: Epistemic Challenge {challenge_id} issued for {proposal_id}.")
    print(json.dumps(challenge, indent=2))

def submit_defense(proposal_id, response_file):
    if not os.path.exists(response_file):
        print(f"ERROR: Response file {response_file} not found.")
        return

    # Ensure a challenge actually exists for this proposal
    challenge_id = None
    if os.path.exists(CHALLENGES_FILE):
        with open(CHALLENGES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    c = json.loads(line)
                    if c.get("proposal_id") == proposal_id: 
                        challenge_id = c.get("challenge_id")
                except: pass

    if not challenge_id:
        print(f"ERROR: Cannot defend. No challenge exists for {proposal_id}.")
        return

    with open(response_file, "r", encoding="utf-8") as f:
        content = f.read()

    proposal = get_proposal(proposal_id)
    drill_tag = proposal.get("drill", False) if proposal else False

    defense_id = f"DEF-{int(time.time())}"
    import hashlib
    defense_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    defense = {
        "defense_id": defense_id,
        "proposal_id": proposal_id,
        "proposal_sha256": proposal.get("proposal_sha256") if proposal else None,
        "challenge_id": challenge_id,
        "defense_sha256": defense_sha256,
        "submitted_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "defense_content": content
    }

    if drill_tag:
        defense["drill"] = True

    with open(DEFENSES_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(defense) + "\n")

    print(f"SUCCESS: Epistemic Defense {defense_id} logged for {proposal_id}.")
    
    # --- PHASE F6: ADVISORY QUALITY SCORING ---
    RUBRIC = {
        "claimed_purpose": ["purpose", "objective", "goal"],
        "assumed_dependency": ["assum", "depend"],
        "missing_evidence": ["evidence", "proof", "guarantee"],
        "falsification_test": ["falsification", "metric", "outcome"],
        "cheapest_safe_probe": ["probe", "scale", "smaller"],
        "risk_if_wrong": ["risk", "blast radius", "wrong", "impact"]
    }
    
    content_lower = content.lower()
    missing_sections = []
    answered_count = 0
    
    for section, keywords in RUBRIC.items():
        if any(kw in content_lower for kw in keywords):
            answered_count += 1
        else:
            missing_sections.append(section)
            
    score = answered_count / len(RUBRIC)
    
    score_record = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "proposal_id": proposal_id,
        "challenge_id": challenge_id,
        "defense_id": defense_id,
        "defense_quality_score": round(score, 2),
        "missing_sections": missing_sections,
        "quality_mode": "ADVISORY_ONLY",
        "rubric_version": "F6_KEYWORD_COMPLETENESS_V1",
        "scoring_semantics": "structural_completeness_not_truth"
    }
    
    if drill_tag:
        score_record["drill"] = True
        
    SCORES_FILE = os.path.join(ESCROW_DIR, "epistemic_defense_scores.jsonl")
    with open(SCORES_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(score_record) + "\n")
        
    print(f"INFO: F6 Defense Quality Score: {score_record['defense_quality_score']:.2f} (Advisory Only)")
    # --- END PHASE F6 ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Axis Epistemic Verifier")
    parser.add_argument("--challenge", type=str, help="Issue a challenge for the given proposal ID.")
    parser.add_argument("--defend", type=str, help="Submit a defense for the given proposal ID.")
    parser.add_argument("--response_file", type=str, help="Path to the response markdown/text file (required for --defend).")
    
    args = parser.parse_args()

    if args.challenge:
        issue_challenge(args.challenge)
    elif args.defend:
        if not args.response_file:
            print("ERROR: --response_file is required when submitting a defense.")
        else:
            submit_defense(args.defend, args.response_file)
    else:
        parser.print_help()
