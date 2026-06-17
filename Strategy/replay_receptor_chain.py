import os
import json
import hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(BASE_DIR, "State")
LEDGER_PATH = os.path.join(STATE_DIR, "receptor_ledger.jsonl")
HEAD_PATH = os.path.join(STATE_DIR, "receptor_chain_head.json")

def replay_chain():
    print("--- Replaying Receptor Chain ---")
    if not os.path.exists(LEDGER_PATH):
        print("No ledger found.")
        return True

    expected_parent = "GENESIS"
    cases = {}

    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for idx, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        receipt = json.loads(line)
        
        # Invariant 1: Chain continuity
        if receipt["parent_receptor_head"] != expected_parent:
            raise ValueError(f"Chain broken at receipt {idx}: Expected parent {expected_parent}, got {receipt['parent_receptor_head']}")
            
        # Verify receipt hash integrity
        payload_bytes = json.dumps(receipt["payload"], sort_keys=True, separators=(",", ":")).encode("utf-8")
        computed_payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        if computed_payload_hash != receipt["payload_hash"]:
            raise ValueError(f"Payload hash mismatch at receipt {idx}")
            
        receipt_base = f"{receipt['event_type']}|{receipt['case_id']}|{receipt['parent_receptor_head']}|{computed_payload_hash}|{receipt['timestamp']}"
        computed_receipt_hash = hashlib.sha256(receipt_base.encode("utf-8")).hexdigest()
        if computed_receipt_hash != receipt["receipt_hash"]:
            raise ValueError(f"Receipt hash mismatch at receipt {idx}")
            
        expected_parent = computed_receipt_hash
        
        case_id = receipt["case_id"]
        event_type = receipt["event_type"]
        
        if case_id not in cases:
            cases[case_id] = {"events": [], "evidence": None, "observation": None}
            
        case = cases[case_id]
        case["events"].append(event_type)
        
        # State tracking for invariant checks
        if event_type in ["RECEPTOR_OBSERVATION_RECORDED", "RECEPTOR_DIFF_OBSERVED"]:
            case["observation"] = receipt["payload"]
        elif event_type in ["RECEPTOR_EVIDENCE_ATTACHED", "RECEPTOR_DIFF_SANDBOXED"]:
            if event_type == "RECEPTOR_EVIDENCE_ATTACHED":
                # Invariant 2: Observation before evidence
                if "RECEPTOR_OBSERVATION_RECORDED" not in case["events"] and "RECEPTOR_DIFF_OBSERVED" not in case["events"]:
                    raise ValueError(f"Invariant 2 Failed: Evidence attached before observation for case {case_id}")
                case["evidence"] = receipt["payload"]
        elif event_type == "RECEPTOR_RATIONALE_SCORED":
            # Rationale must come after evidence
            if "RECEPTOR_EVIDENCE_ATTACHED" not in case["events"]:
                raise ValueError(f"Invariant Failed: Rationale scored before evidence for case {case_id}")
            case["rationale"] = receipt["payload"]
        elif event_type in ["RECEPTOR_DELTA_ACCEPTED", "RECEPTOR_DELTA_QUARANTINED"]:
            # Invariant 3: Evidence before verdict
            if "RECEPTOR_EVIDENCE_ATTACHED" not in case["events"]:
                raise ValueError(f"Invariant 3 Failed: Verdict rendered before evidence for case {case_id}")
            # Rationale before verdict
            if "RECEPTOR_RATIONALE_SCORED" not in case["events"]:
                raise ValueError(f"Invariant Failed: Verdict rendered before rationale scored for case {case_id}")
            
            # Invariant 6: No orphan verdicts
            if not case["observation"] or not case["evidence"]:
                raise ValueError(f"Invariant 6 Failed: Orphan verdict for case {case_id}")

            if event_type == "RECEPTOR_DELTA_ACCEPTED":
                # Invariant 4: Accepted verdict requires syntax_valid == true and hash match
                ev = case["evidence"]
                obs = case["observation"]
                if not ev.get("syntax_valid"):
                    raise ValueError(f"Invariant 4 Failed: Invalid evidence promoted for case {case_id} (syntax_valid=False)")
                    
                if obs.get("schema") == "axis.code_diff.v1":
                    from receptor_pipeline import apply_diff_to_content
                    target_file = os.path.join(BASE_DIR, obs["target_file"])
                    if os.path.exists(target_file):
                        with open(target_file, "r", encoding="utf-8") as f:
                            current_content = f.read()
                        current_hash = hashlib.sha256(current_content.encode("utf-8")).hexdigest()
                        if current_hash != obs["original_hash"]:
                            raise ValueError(f"Invariant 4 Failed: target file drifted after observation for case {case_id}")
                            
                        new_content = apply_diff_to_content(current_content, obs["diff_content"])
                        trial_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()
                        if trial_hash != ev.get("verified_hash"):
                            raise ValueError(f"Invariant 4 Failed: Recomputed diff trial hash mismatch for case {case_id}")
                    else:
                        raise ValueError(f"Invariant 4 Failed: target file missing for case {case_id}")
                else:
                    if ev.get("verified_hash") != obs.get("content_hash"):
                        raise ValueError(f"Invariant 4 Failed: Invalid evidence promoted for case {case_id} (hash mismatch)")
            elif event_type == "RECEPTOR_DELTA_QUARANTINED":
                # Invariant 5: Quarantined verdict requires explicit failed gate
                if not receipt["payload"].get("reason"):
                    raise ValueError(f"Invariant 5 Failed: Quarantined without reason for case {case_id}")

    # Invariant 7: Final replay head matches stored head
    if os.path.exists(HEAD_PATH):
        with open(HEAD_PATH, "r", encoding="utf-8") as f:
            stored_head = json.load(f).get("head")
        if stored_head != expected_parent:
            raise ValueError(f"Invariant 7 Failed: Stored head {stored_head} does not match replay head {expected_parent}")
            
    print(f"Replay successful. {len(lines)} receipts verified across {len(cases)} cases.")
    print("All 7 Invariants Passed.")
    return True

if __name__ == "__main__":
    replay_chain()
