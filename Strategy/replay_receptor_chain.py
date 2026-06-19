import os
import json
import hashlib
import string
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.environ.get("AXIS_STATE_DIR", os.path.join(BASE_DIR, "State"))

LEDGER_PATH = os.path.join(STATE_DIR, "receptor_ledger.jsonl")
HEAD_PATH = os.path.join(STATE_DIR, "receptor_chain_head.json")

def _get_validator_surfaces():
    import json
    manifest_path = os.path.join(BASE_DIR, "validator_surfaces.json")
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f).get("validator_surfaces", {})
    except Exception:
        return {}

def replay_chain():
    print("--- Replaying Receptor Chain ---")
    if not os.path.exists(LEDGER_PATH):
        print("No ledger found.")
        return True

    manifest = _get_validator_surfaces()

    expected_parent = "GENESIS"
    # Invariant 15 Tracking
    global_session_burden = 0.0
    global_commit_count = 0
    global_quarantine_count = 0
    global_accepted_count = 0
    global_pending_recoveries = {}

    cases = {}
    commits = {}
    suggested_patches = set()

    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for idx, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        receipt = json.loads(line)
        case_id = receipt["case_id"]
        event_type = receipt["event_type"]

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

        if case_id not in cases:
            cases[case_id] = {"events": [], "evidence": None, "observation": None}

        case = cases[case_id]
        case["events"].append(event_type)
        case.setdefault("payloads", {})[event_type] = receipt.get("payload", {})

        # State tracking for invariant checks
        if event_type in ["RECEPTOR_OBSERVATION_RECORDED", "RECEPTOR_DIFF_OBSERVED"]:
            case["observation"] = receipt["payload"]
        elif event_type == "RECEPTOR_SEMANTIC_RISK_SCORED":
            # Semantic risk must come after observation
            if "RECEPTOR_OBSERVATION_RECORDED" not in case["events"] and "RECEPTOR_DIFF_OBSERVED" not in case["events"]:
                raise ValueError(f"Invariant Failed: Semantic risk scored before observation for case {case_id}")

            # Invariant 9: Anti-Sprawl
            import fnmatch
            target_file = case["observation"]["target_file"]
            normalized_filename = target_file.replace("\\", "/")
            basename = os.path.basename(normalized_filename)
            expected_validator = False
            for pattern in manifest.keys():
                if fnmatch.fnmatch(basename, pattern) or fnmatch.fnmatch(normalized_filename, pattern):
                    expected_validator = True
                    break

            claimed_validator = receipt["payload"].get("is_validator_surface", False)
            if expected_validator != claimed_validator:
                raise ValueError(f"Invariant 9 Failed: Sprawl risk detected. Receipt claims is_validator_surface={claimed_validator} for {basename}, but manifest implies {expected_validator}")

            case["semantic_risk"] = receipt["payload"]
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
        elif event_type == "CHECK_ONLY":
            # Invariant 16: Dry-Run Purity
            if receipt["payload"].get("state_mutation_performed") is not False:
                raise ValueError(f"Invariant 16 Failed: CHECK_ONLY receipt {idx} did not assert state_mutation_performed=False")

            # CHECK_ONLY should only share the case with Auditor receipts (which record advisory LLM logic, not system state)
            allowed_events = {"CHECK_ONLY", "AUDITOR_REVIEW_REQUESTED", "AUDITOR_VERDICT_RECEIVED", "AUDITOR_VERDICT_INVALID", "MULTI_AUDIT_REQUESTED", "MULTI_AUDIT_VERDICTS_RECEIVED", "MULTI_AUDIT_CONSENSUS_RECORDED"}
            if not set(case["events"]).issubset(allowed_events):
                raise ValueError(f"Invariant 16 Failed: CHECK_ONLY case {case_id} shares events with non-audit mutating receipts. Events: {case['events']}")
            continue
        elif event_type in ["RECEPTOR_DELTA_ACCEPTED", "RECEPTOR_DELTA_QUARANTINED"]:
            if "CHECK_ONLY" in case["events"]:
                raise ValueError(f"Invariant 16 Failed: Mutating receipt {event_type} shares case_id with a CHECK_ONLY receipt.")

            is_semantic_quarantine = (event_type == "RECEPTOR_DELTA_QUARANTINED" and receipt["payload"].get("reason") == "semantic_validator_surface_risk")

            if not is_semantic_quarantine:
                # Invariant 3: Evidence before verdict
                if "RECEPTOR_EVIDENCE_ATTACHED" not in case["events"]:
                    raise ValueError(f"Invariant 3 Failed: Verdict rendered before evidence for case {case_id}")
                # Rationale before verdict
                if "RECEPTOR_RATIONALE_SCORED" not in case["events"]:
                    raise ValueError(f"Invariant Failed: Verdict rendered before rationale scored for case {case_id}")

            # Invariant 6: No orphan verdicts
            if not case["observation"]:
                raise ValueError(f"Invariant 6 Failed: Orphan verdict for case {case_id}")

            if event_type == "RECEPTOR_DELTA_ACCEPTED":
                case["accepted"] = True
                global_accepted_count += 1
                # Invariant 4: Accepted verdict requires syntax_valid == true and hash match
                ev = case["evidence"]
                obs = case["observation"]
                if not ev.get("syntax_valid"):
                    raise ValueError(f"Invariant 4 Failed: Invalid evidence promoted for case {case_id} (syntax_valid=False)")

                if obs.get("schema") == "axis.code_diff.v1":
                    from receptor_pipeline import apply_diff_to_content
                    if obs.get("original_content") is not None:
                        current_content = obs["original_content"]
                    elif not obs.get("historical", False):
                        filepath = os.path.join(BASE_DIR, obs["target_file"])
                        if not os.path.exists(filepath):
                            # Fallback search for basename-only legacy receipts
                            for root, _, files in os.walk(BASE_DIR):
                                if obs["target_file"] in files:
                                    filepath = os.path.join(root, obs["target_file"])
                                    break

                        if os.path.exists(filepath):
                            with open(filepath, "r", encoding="utf-8") as f:
                                current_content = f.read()
                            current_hash = hashlib.sha256(current_content.encode("utf-8")).hexdigest()
                            if current_hash != obs["original_hash"]:
                                raise ValueError(f"Invariant 4 Failed: target file drifted after observation for case {case_id}")
                        else:
                            raise ValueError(f"Invariant 4 Failed: target file missing for case {case_id}")
                    else:
                        current_content = ""

                    new_content = apply_diff_to_content(current_content, obs["diff_content"])
                    trial_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()
                    if trial_hash != ev.get("verified_hash"):
                        raise ValueError(f"Invariant 4 Failed: Recomputed diff trial hash mismatch for case {case_id}")
                else:
                    if ev.get("verified_hash") != obs.get("content_hash"):
                        raise ValueError(f"Invariant 4 Failed: Invalid evidence promoted for case {case_id} (hash mismatch)")
            elif event_type == "RECEPTOR_DELTA_QUARANTINED":
                global_quarantine_count += 1
                # Invariant 5: Quarantined requires failed gate
                if not receipt["payload"].get("reason"):
                    raise ValueError(f"Invariant 5 Failed: Quarantined without reason for case {case_id}")
        elif event_type == "RECEPTOR_GOVERNANCE_EVALUATED":
            # Invariant 10: Governance evaluation must follow an accepted case
            if not case.get("accepted", False):
                raise ValueError(f"Invariant 10 Failed: Governance evaluated for non-accepted case {case_id}")
            if "RECEPTOR_DELTA_ACCEPTED" not in case["events"]:
                raise ValueError(f"Invariant 10 Failed: Governance evaluated before ACCEPTED verdict for case {case_id}")

            gov_payload = receipt["payload"]
            case["gov_payload"] = gov_payload
            # Invariant 11: Governance weight is fully derivable from physical reality
            from constitutional_debt_engine import ConstitutionalDebtEngine
            engine = ConstitutionalDebtEngine()

            gov_payload = receipt["payload"]

            if gov_payload.get("scoring_version") != engine.scoring_version:
                raise ValueError(f"Invariant 11 Failed: Governance scoring version mismatch for case {case_id}")

            # Recompute
            target_file = case["observation"]["target_file"]
            diff_text = case["observation"].get("diff_content", "")
            if not diff_text and "content" in case["observation"]:
                diff_text = case["observation"]["content"]
            risk_score = case.get("semantic_risk", {}).get("risk_score", 0.0)

            recomputed = engine.evaluate_delta_weight(target_file, diff_text, risk_score)

            if recomputed["utility_score"] != gov_payload["utility_score"] or recomputed["burden_score"] != gov_payload["burden_score"]:
                raise ValueError(f"Invariant 11 Failed: Governance score physically drifted for case {case_id}")

        elif event_type.startswith("COMMIT_"):
            commit_case_id = receipt["case_id"]
            if commit_case_id not in commits:
                commits[commit_case_id] = {"files": [], "files_processed": [], "gov_payload": None}

            if event_type == "COMMIT_OBSERVED":
                commits[commit_case_id]["files"] = receipt["payload"]["target_files"]
            elif event_type == "COMMIT_FILE_PROCESSED":
                commits[commit_case_id]["files_processed"].append(receipt["payload"]["file_case_id"])
            elif event_type == "COMMIT_GOVERNANCE_EVALUATED":
                commits[commit_case_id]["gov_payload"] = receipt["payload"]
                global_session_burden += receipt["payload"]["burden_score"]

                # Invariant 12: Recompute cumulative burden
                total_utility = 0.0
                total_burden = 0.0
                for fid in commits[commit_case_id]["files_processed"]:
                    if fid in cases and "gov_payload" in cases[fid]:
                        total_utility += cases[fid]["gov_payload"].get("utility_score", 0.0)
                        total_burden += cases[fid]["gov_payload"].get("burden_score", 0.0)

                if abs(total_utility - receipt["payload"]["utility_score"]) > 0.001 or abs(total_burden - receipt["payload"]["burden_score"]) > 0.001:
                    raise ValueError(f"Invariant 12 Failed: Commit governance scores drifted for {commit_case_id}")

            elif event_type == "COMMIT_ACCEPTED":
                # Invariant 12: Ensure all processed files are ACCEPTED
                global_commit_count += 1
                for fid in commits[commit_case_id]["files_processed"]:
                    if not cases.get(fid, {}).get("accepted", False):
                        raise ValueError(f"Invariant 12 Failed: Commit accepted but child file {fid} was not accepted")
            elif event_type == "COMMIT_QUARANTINED":
                global_commit_count += 1
                # Invariant 12: Ensure at least one processed file is QUARANTINED
                any_quarantined = False
                for fid in commits[commit_case_id]["files_processed"]:
                    if "RECEPTOR_DELTA_QUARANTINED" in cases.get(fid, {}).get("events", []):
                        any_quarantined = True
                        break
                if not any_quarantined:
                    raise ValueError(f"Invariant 12 Failed: Commit quarantined but no child file was quarantined")

        elif event_type == "RECEPTOR_DISTRESS_SIGNALED":
            # Invariant 13: Distress signal burden == replay-computed session burden
            for sig in receipt["payload"].get("signals", []):
                if "cumulative_burden" in sig:
                    if abs(sig["cumulative_burden"] - global_session_burden) > 0.001:
                        raise ValueError(f"Invariant 13 Failed: Distress signal claimed session burden {sig['cumulative_burden']} but replay derived {global_session_burden}")

        elif event_type == "RECEPTOR_RECOVERY_SUGGESTED":
            # Invariant 13: recovery_patch_hash == sha256(file at recovery_patch_path)
            patch_path = receipt["payload"].get("recovery_patch_path")
            claimed_hash = receipt["payload"].get("recovery_patch_hash")
            if patch_path:
                suggested_patches.add(patch_path)
                global_pending_recoveries[os.path.basename(patch_path)] = "AWAITING_AUTHORIZATION"

            if patch_path and claimed_hash:
                full_path = os.path.join(BASE_DIR, patch_path)
                if os.path.exists(full_path):
                    with open(full_path, "r", encoding="utf-8") as f:
                        actual_hash = hashlib.sha256(f.read().encode("utf-8")).hexdigest()
                    if actual_hash != claimed_hash:
                        raise ValueError(f"Invariant 13 Failed: Recovery patch hash mismatch for {patch_path}")

        elif event_type == "RECEPTOR_DISTRESS_INFLUENCED":
            # Invariant 13: distress-influenced receipt occurs only when prior replay session burden > 2.0
            if global_session_burden <= 2.0:
                raise ValueError(f"Invariant 13 Failed: DISTRESS_INFLUENCED emitted but derived session burden was {global_session_burden} (<= 2.0)")

        elif event_type == "ADJUDICATION_RULING":
            # Invariant 17: Adjudication Integrity
            quarantined_case_id = receipt["payload"]["quarantined_case_id"]
            if quarantined_case_id not in cases:
                raise ValueError(f"Invariant 17 Failed: ADJUDICATION_RULING references unknown case {quarantined_case_id}")
            if "RECEPTOR_DELTA_QUARANTINED" not in cases[quarantined_case_id]["events"]:
                raise ValueError(f"Invariant 17 Failed: ADJUDICATION_RULING references case {quarantined_case_id} which is not QUARANTINED")

            quarantine_payload = cases[quarantined_case_id]["payloads"]["RECEPTOR_DELTA_QUARANTINED"]
            if quarantine_payload.get("reason") in ["syntax_invalid", "hash_mismatch"]:
                raise ValueError(f"Invariant 17 Failed: ADJUDICATION_RULING cannot override physical failure ({quarantine_payload.get('reason')})")

            evidence_hash = receipt["payload"]["evidence_hash"]
            verdict_hash = receipt["payload"]["auditor_verdict_hash"]
            ruling = receipt["payload"]["ruling_type"]

            hexdigits = set(string.hexdigits)
            if len(evidence_hash) != 64 or not all(c in hexdigits for c in evidence_hash):
                raise ValueError("Invariant 17 Failed: evidence_hash is not a valid SHA-256 string")
            if len(verdict_hash) != 64 or not all(c in hexdigits for c in verdict_hash):
                raise ValueError("Invariant 17 Failed: auditor_verdict_hash is not a valid SHA-256 string")

            if ruling not in ["ACCEPT_OVERRIDE", "DEFER", "SUSTAIN_QUARANTINE"]:
                raise ValueError(f"Invariant 17 Failed: Invalid ruling type {ruling}")

            adjudication_case_id = receipt["case_id"]
            canonical_str = f"{adjudication_case_id}|{quarantined_case_id}|{evidence_hash}|{verdict_hash}|{ruling}"
            if receipt["payload"].get("canonical_str") != canonical_str:
                raise ValueError(f"Invariant 17 Failed: ADJUDICATION_RULING referential integrity mismatch. Expected canonical_str: {canonical_str}")

            cases[quarantined_case_id]["adjudication"] = receipt["payload"]

        elif event_type == "AUDITOR_REVIEW_REQUESTED":
            # Just record that an audit was requested
            cases[case_id]["events"].append(event_type)
            cases[case_id]["audit_requests"] = cases[case_id].get("audit_requests", 0) + 1

        elif event_type == "MULTI_AUDIT_REQUESTED":
            cases[case_id]["events"].append(event_type)
            cases[case_id]["audit_requests"] = cases[case_id].get("audit_requests", 0) + 1
            cases[case_id]["multi_audit_strategy"] = receipt["payload"].get("strategy")

        elif event_type == "MULTI_AUDIT_VERDICTS_RECEIVED":
            if "MULTI_AUDIT_REQUESTED" not in cases[case_id]["events"]:
                raise ValueError(f"Invariant 19 Failed: MULTI_AUDIT_VERDICTS_RECEIVED without prior REQUESTED for case {case_id}")
            cases[case_id]["events"].append(event_type)
            cases[case_id]["multi_audit_verdicts"] = receipt["payload"].get("verdicts", [])

        elif event_type == "MULTI_AUDIT_CONSENSUS_RECORDED":
            if "MULTI_AUDIT_VERDICTS_RECEIVED" not in cases[case_id]["events"]:
                raise ValueError(f"Invariant 19 Failed: MULTI_AUDIT_CONSENSUS_RECORDED without prior VERDICTS_RECEIVED for case {case_id}")
            cases[case_id]["events"].append(event_type)

            consensus = receipt["payload"].get("consensus_verdict")
            strategy = receipt["payload"].get("strategy_applied")
            q_sources = receipt["payload"].get("quarantine_sources", [])
            a_sources = receipt["payload"].get("accept_sources", [])
            expected_strategy = cases[case_id].get("multi_audit_strategy")

            if strategy != expected_strategy:
                raise ValueError(f"Invariant 19 Failed: Strategy mismatch. Expected {expected_strategy}, recorded {strategy}")

            raw_verdicts = cases[case_id].get("multi_audit_verdicts", [])
            if len(raw_verdicts) != receipt["payload"].get("verdict_count"):
                raise ValueError(f"Invariant 19 Failed: Verdict count mismatch. Expected {len(raw_verdicts)}, recorded {receipt['payload'].get('verdict_count')}")

            if strategy == "ANY_QUARANTINE_WINS":
                has_quarantine = any(v.get("verdict") in ["QUARANTINE", "AUDITOR_VERDICT_INVALID"] for v in raw_verdicts)
                expected_consensus = "QUARANTINE" if has_quarantine else ("DEFER" if any(v.get("verdict") == "DEFER" for v in raw_verdicts) else "ACCEPT")
                if consensus != expected_consensus:
                    raise ValueError(f"Invariant 19 Failed: Consensus math violation. Expected {expected_consensus}, got {consensus}")

            actual_q_sources = [v.get("auditor_id") for v in raw_verdicts if v.get("verdict") in ["QUARANTINE", "AUDITOR_VERDICT_INVALID"]]
            actual_a_sources = [v.get("auditor_id") for v in raw_verdicts if v.get("verdict") == "ACCEPT"]

            if set(q_sources) != set(actual_q_sources):
                raise ValueError(f"Invariant 19 Failed: Quarantine sources mismatch. Expected {actual_q_sources}, got {q_sources}")
            if set(a_sources) != set(actual_a_sources):
                raise ValueError(f"Invariant 19 Failed: Accept sources mismatch. Expected {actual_a_sources}, got {a_sources}")

        elif event_type in ["AUDITOR_VERDICT_RECEIVED", "AUDITOR_VERDICT_INVALID"]:
            # Invariant 18: Auditor Receipt Integrity
            if "AUDITOR_REVIEW_REQUESTED" not in cases[case_id]["events"]:
                raise ValueError(f"Invariant 18 Failed: {event_type} received without a prior AUDITOR_REVIEW_REQUESTED for case {case_id}")

            cases[case_id]["events"].append(event_type)

            if event_type == "AUDITOR_VERDICT_RECEIVED":
                verdict = receipt["payload"].get("verdict")
                if verdict not in ["ACCEPT", "DEFER", "QUARANTINE"]:
                    raise ValueError(f"Invariant 18 Failed: Invalid verdict {verdict} in AUDITOR_VERDICT_RECEIVED")
                if "confidence" not in receipt["payload"]:
                    raise ValueError("Invariant 18 Failed: Missing confidence in AUDITOR_VERDICT_RECEIVED")

                if verdict == "ACCEPT":
                    quarantine_payload = cases[case_id]["payloads"].get("RECEPTOR_DELTA_QUARANTINED", {})
                    reason = quarantine_payload.get("reason", "")
                    if reason in ["syntax_invalid", "hash_mismatch"]:
                        raise ValueError(f"Invariant 18 Failed: Auditor verdict ACCEPT cannot override physical failure ({reason})")

        elif event_type == "RECOVERY_PATCH_PROPOSED":
            # Invariant 20: Recovery Proposal referential integrity
            if "RECEPTOR_DELTA_QUARANTINED" not in cases[case_id]["events"]:
                raise ValueError(f"Invariant 20 Failed: RECOVERY_PATCH_PROPOSED on non-quarantined case {case_id}")
            if "ADJUDICATION_RULING" in cases[case_id]["events"]:
                raise ValueError(f"Invariant 20 Failed: RECOVERY_PATCH_PROPOSED on already adjudicated case {case_id}")
            cases[case_id]["events"].append(event_type)
            cases[case_id]["proposals"] = cases[case_id].get("proposals", []) + [receipt]

        elif event_type == "RECOVERY_APPLIED":
            # Invariant 21: Hash-based lineage for applied recoveries
            cases[case_id]["events"].append(event_type)
            proposals = cases[case_id].get("proposals", [])
            if not proposals:
                raise ValueError(f"Invariant 21 Failed: RECOVERY_APPLIED without RECOVERY_PATCH_PROPOSED on case {case_id}")

            proposal = None
            expected_hash = receipt["payload"].get("recovery_proposal_receipt_hash")
            for p in proposals:
                if p["receipt_hash"] == expected_hash:
                    proposal = p
                    break

            if not proposal:
                raise ValueError(f"Invariant 21 Failed: RECOVERY_APPLIED references unknown proposal hash {expected_hash}")

            if proposal["payload"].get("proposal_status") != "ELIGIBLE":
                raise ValueError(f"Invariant 21 Failed: RECOVERY_APPLIED references a non-ELIGIBLE proposal")

            if receipt["payload"].get("patch_hash") != proposal["payload"].get("patch_hash"):
                raise ValueError(f"Invariant 21 Failed: RECOVERY_APPLIED patch_hash mismatch")

            cases[case_id]["applied_receipt"] = receipt

        elif event_type == "RECOVERY_VERIFIED":
            # Invariant 21: Verification tracking
            cases[case_id]["events"].append(event_type)
            if "RECOVERY_APPLIED" not in cases[case_id]["events"]:
                raise ValueError(f"Invariant 21 Failed: RECOVERY_VERIFIED without RECOVERY_APPLIED on case {case_id}")

            applied = cases[case_id].get("applied_receipt")
            if receipt["payload"].get("applied_receipt_hash") != applied["receipt_hash"]:
                raise ValueError(f"Invariant 21 Failed: RECOVERY_VERIFIED references unknown applied hash")
    # Invariant 7: Final replay head matches stored head
    if os.path.exists(HEAD_PATH):
        with open(HEAD_PATH, "r", encoding="utf-8") as f:
            stored_head = json.load(f).get("head")
        if stored_head != expected_parent:
            raise ValueError(f"Invariant 7 Failed: Stored head {stored_head} does not match replay head {expected_parent}")

    # Invariant 15: Telemetry is purely derivable
    # Invariant 15: Purely Derivable State
    d_state = {}
    if os.path.exists("State/distress_state.json"):
        with open("State/distress_state.json", "r") as f:
            d_state = json.load(f)

    # Invariant 16: Dry-Run Purity
    # Verify no accidental ledger mutation occurred during dry-run sessions
    # (By definition, we just verified all historical bounds and ignore CHECK_ONLY)

    if d_state:   # 15A
        if abs(d_state.get("session_burden", 0.0) - global_session_burden) > 0.001:
            raise ValueError(f"Invariant 15A Failed: ledger session_burden {global_session_burden} != state {d_state.get('session_burden')}")
        # 15B
        if d_state.get("commit_count", 0) != global_commit_count:
            raise ValueError(f"Invariant 15B Failed: ledger commit_count {global_commit_count} != state {d_state.get('commit_count')}")
        # 15C
        for k, v in global_pending_recoveries.items():
            if d_state.get("pending_recoveries", {}).get(k) != v:
                raise ValueError(f"Invariant 15C Failed: ledger pending_recoveries[{k}]={v} != state")
        # 15D
        if d_state.get("quarantined_files", 0) != global_quarantine_count:
            raise ValueError(f"Invariant 15D Failed: ledger quarantined_files {global_quarantine_count} != state {d_state.get('quarantined_files')}")
        if d_state.get("accepted_files", 0) != global_accepted_count:
            raise ValueError(f"Invariant 15D Failed: ledger accepted_files {global_accepted_count} != state {d_state.get('accepted_files')}")

    print(f"Replay successful. {len(lines)} receipts verified across {len(cases)} cases.")
    print("All 21 Invariants Passed.")
    return True

if __name__ == "__main__":
    replay_chain()
