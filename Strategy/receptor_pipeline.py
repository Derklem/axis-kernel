import os
import sys
import json
import hashlib
import py_compile
import subprocess
import time
import uuid
import hmac

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.path.join(BASE_DIR, "State")
OBSERVATIONS_DIR = os.path.join(STATE_DIR, "Observations")
QUARANTINE_DIR = os.path.join(STATE_DIR, "Quarantine")
ACCEPTED_REFACTORS_DIR = os.path.join(STATE_DIR, "AcceptedRefactors")
LEDGER_PATH = os.path.join(STATE_DIR, "receptor_ledger.jsonl")
HEAD_PATH = os.path.join(STATE_DIR, "receptor_chain_head.json")
SANDBOX_DIR = os.path.join(STATE_DIR, "ReceptorSandbox")
MAIN_LEDGER_PATH = os.path.join(STATE_DIR, "forensic_witness_ledger.jsonl")

for d in [OBSERVATIONS_DIR, QUARANTINE_DIR, ACCEPTED_REFACTORS_DIR, SANDBOX_DIR]:
    os.makedirs(d, exist_ok=True)

def apply_diff_to_content(original_content, diff_content):
    diff_lines = diff_content.splitlines()
    original_lines = original_content.splitlines()
    new_lines = original_lines.copy()
    
    hunks = []
    current_hunk = None
    for line in diff_lines:
        if line.startswith('---') or line.startswith('+++'):
            continue
        if line.startswith('@@'):
            parts = line.split(' ')
            old_range = parts[1][1:]
            old_start = int(old_range.split(',')[0])
            current_hunk = {"start": old_start, "lines": []}
            hunks.append(current_hunk)
        elif current_hunk is not None:
            current_hunk["lines"].append(line)
            
    # Apply backwards
    hunks.sort(key=lambda h: h["start"], reverse=True)
    for hunk in hunks:
        start_idx = hunk["start"] - 1
        
        old_count = sum(1 for l in hunk["lines"] if l.startswith(' ') or l.startswith('-'))
        
        new_hunk_lines = []
        for l in hunk["lines"]:
            if l.startswith('+'):
                new_hunk_lines.append(l[1:])
            elif l.startswith(' '):
                new_hunk_lines.append(l[1:])
            # '-' lines are discarded
            
        new_lines[start_idx:start_idx+old_count] = new_hunk_lines
        
    # Rejoin with newlines (add trailing newline if original had one or standard python file format)
    return "\n".join(new_lines) + ("\n" if original_content.endswith("\n") else "")

class ReceptorPipeline:
    def __init__(self):
        self.dry_run = False
        self.record_check = False
        if not os.path.exists(HEAD_PATH):
            self._write_head("GENESIS")

    def _get_head(self):
        if os.path.exists(HEAD_PATH):
            with open(HEAD_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("head", "GENESIS")
        return "GENESIS"

    def _write_head(self, head_hash):
        with open(HEAD_PATH, "w", encoding="utf-8") as f:
            json.dump({"head": head_hash}, f, indent=2)

    def _emit_receipt(self, event_type, case_id, payload_dict):
        audit_events = ["AUDITOR_REVIEW_REQUESTED", "AUDITOR_VERDICT_RECEIVED", "AUDITOR_VERDICT_INVALID"]
        if self.dry_run and event_type != "CHECK_ONLY" and event_type not in audit_events:
            return
        if event_type == "CHECK_ONLY" and not self.record_check:
            return
        if event_type in audit_events and not self.record_check:
            return
            
        parent_head = self._get_head()
        payload_bytes = json.dumps(payload_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        
        timestamp = time.time()
        
        receipt_base = f"{event_type}|{case_id}|{parent_head}|{payload_hash}|{timestamp}"
        receipt_hash = hashlib.sha256(receipt_base.encode("utf-8")).hexdigest()
        
        receipt = {
            "event_type": event_type,
            "case_id": case_id,
            "parent_receptor_head": parent_head,
            "payload_hash": payload_hash,
            "receipt_hash": receipt_hash,
            "timestamp": timestamp,
            "payload": payload_dict
        }
        
        with open(LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(receipt, sort_keys=True) + "\n")
            
        self._write_head(receipt_hash)
        return receipt

    def observe_file_delta(self, filepath):
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        h = hashlib.sha256(content.encode("utf-8")).hexdigest()
        filename = os.path.basename(filepath)
        case_id = str(uuid.uuid4())
        
        claim = {
            "schema": "axis.code_refactor.v1",
            "target_file": filename,
            "content_hash": h,
            "observation_timestamp": time.time()
        }
        
        self._emit_receipt("RECEPTOR_OBSERVATION_RECORDED", case_id, claim)
        return case_id, filepath, claim

    def observe_git_diff(self, diff_path, target_filepath):
        if not os.path.exists(diff_path) or not os.path.exists(target_filepath):
            return None
            
        with open(diff_path, "r", encoding="utf-8") as f:
            diff_content = f.read()
            
        with open(target_filepath, "r", encoding="utf-8") as f:
            original_content = f.read()
            
        original_hash = hashlib.sha256(original_content.encode("utf-8")).hexdigest()
        diff_hash = hashlib.sha256(diff_content.encode("utf-8")).hexdigest()
        filename = os.path.basename(target_filepath)
        case_id = str(uuid.uuid4())
        
        claim = {
            "schema": "axis.code_diff.v1",
            "target_file": filename,
            "original_hash": original_hash,
            "diff_hash": diff_hash,
            "observation_timestamp": time.time(),
            "diff_content": diff_content
        }
        
        self._emit_receipt("RECEPTOR_DIFF_OBSERVED", case_id, claim)
        return case_id, target_filepath, claim

    def _get_validator_surfaces(self):
        import json, os
        manifest_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validator_surfaces.json")
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("validator_surfaces", {})
        except Exception:
            return {
                "replay_receptor_chain.py": ["fallback"],
                "receptor_pipeline.py": ["fallback"]
            }

    def _is_validator_surface(self, filename):
        import fnmatch
        import os
        normalized_filename = filename.replace("\\", "/")
        basename = os.path.basename(normalized_filename)
        surfaces = self._get_validator_surfaces()
        for pattern in surfaces.keys():
            if fnmatch.fnmatch(basename, pattern) or fnmatch.fnmatch(normalized_filename, pattern):
                return True, surfaces[pattern]
        return False, None

    def evaluate_semantic_risk(self, target_file, diff_content):
        import os
        flags = []
        score = 0.0
        
        basename = os.path.basename(target_file)
        
        if basename == "validator_surfaces.json":
            # Count added and removed lines
            added = [l for l in diff_content.splitlines() if l.startswith("+") and not l.startswith("+++")]
            removed = [l for l in diff_content.splitlines() if l.startswith("-") and not l.startswith("---")]
            if len(added) > len(removed):
                flags.append("manifest_expansion")
                score += 1.0
            if len(removed) > 0:
                flags.append("manifest_shrinkage")
                score += 1.0
        
        # Heuristics for weakening or bypassing
        if "if False:" in diff_content or "+    pass" in diff_content or "+        pass" in diff_content:
            flags.append("invariant_weakening")
            score += 0.5
            
        if "ABORT:" in diff_content or "RECEPTOR_CHAIN_COMMITTED_TO_MAIN_LEDGER" in diff_content:
            # Maybe modifying commit logic
            flags.append("commit_guard_mutation")
            score += 0.5
            
        if "QUARANTINED" in diff_content and "ACCEPTED" in diff_content:
            flags.append("quarantine_bypass")
            score += 0.5
            
        if score > 1.0:
            score = 1.0
            
        return score, flags

    def process_claim(self, case_id, filepath, claim):
        print(f"\n--- Ingesting Observation: {claim['target_file']} ---")
        
        # Phase 198.4/198.5 Semantic Risk Flagging
        is_validator, justification = self._is_validator_surface(claim['target_file'])
        semantic_risk_score = 0.0
        semantic_risk_flags = []
        
        if claim["schema"] == "axis.code_diff.v1":
            semantic_risk_score, semantic_risk_flags = self.evaluate_semantic_risk(claim['target_file'], claim["diff_content"])
            
        risk_receipt = {
            "is_validator_surface": is_validator,
            "validator_justification": justification,
            "risk_score": semantic_risk_score,
            "risk_flags": semantic_risk_flags
        }
        self._emit_receipt("RECEPTOR_SEMANTIC_RISK_SCORED", case_id, risk_receipt)
        
        if is_validator and semantic_risk_score > 0.0:
            print(">> FAILED: semantic_validator_surface_risk")
            self._emit_receipt("RECEPTOR_DELTA_QUARANTINED", case_id, {"reason": "semantic_validator_surface_risk"})
            return "QUARANTINED", None
        
        print("Gathering evidence...")
        evidence = {}
        
        if claim["schema"] == "axis.code_diff.v1":
            try:
                if claim.get("historical"):
                    original_content = claim["original_content"]
                else:
                    with open(filepath, "r", encoding="utf-8") as f:
                        original_content = f.read()
                        
                new_content = apply_diff_to_content(original_content, claim["diff_content"])
                
                if self.dry_run:
                    import tempfile
                    case_sandbox = tempfile.mkdtemp()
                else:
                    case_sandbox = os.path.join(SANDBOX_DIR, case_id)
                    os.makedirs(case_sandbox, exist_ok=True)
                    
                try:
                    trial_path = os.path.join(case_sandbox, claim["target_file"])
                    
                    with open(trial_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                        
                    self._emit_receipt("RECEPTOR_DIFF_SANDBOXED", case_id, {"sandbox_path": trial_path})
                    
                    if claim["target_file"].endswith(".py"):
                        py_compile.compile(trial_path, doraise=True)
                    elif claim["target_file"].endswith(".json"):
                        with open(trial_path, "r", encoding="utf-8") as json_f:
                            json.load(json_f)
                    evidence["syntax_valid"] = True
                    
                    trial_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()
                    evidence["verified_hash"] = trial_hash
                    evidence["is_diff"] = True
                finally:
                    if self.dry_run:
                        import shutil
                        shutil.rmtree(case_sandbox, ignore_errors=True)
                        
            except Exception as e:
                evidence["syntax_valid"] = False
                evidence["syntax_error"] = str(e)
                evidence["is_diff"] = True
        else:
            try:
                py_compile.compile(filepath, doraise=True)
                evidence["syntax_valid"] = True
            except Exception as e:
                evidence["syntax_valid"] = False
                evidence["syntax_error"] = str(e)
                
            with open(filepath, "r", encoding="utf-8") as f:
                h = hashlib.sha256(f.read().encode("utf-8")).hexdigest()
            evidence["verified_hash"] = h
            evidence["is_diff"] = False
        
        self._emit_receipt("RECEPTOR_EVIDENCE_ATTACHED", case_id, evidence)
        
        print("Scoring rationale...")
        rationale_str = f"syntax_valid={evidence.get('syntax_valid', False)}"
        if evidence.get("is_diff"):
            rationale_str += "; sandbox_trial_derivable=true"
        else:
            rationale_str += "; hash_continuity=true"
            
        confidence = 1.0 if evidence.get("syntax_valid") else 0.0
        
        # Adversarial test overrides
        if "adversarial_rationale" in claim:
            rationale_str = claim["adversarial_rationale"]
            confidence = claim.get("adversarial_confidence", 1.0)
            
        rationale = {
            "verdict_rationale": rationale_str,
            "confidence_score": confidence,
            "authority": "non_authoritative_metadata"
        }
        
        self._emit_receipt("RECEPTOR_RATIONALE_SCORED", case_id, rationale)
        
        print("Evaluating gates...")
        failed_gate = None
        if not evidence.get("syntax_valid"):
            failed_gate = "syntax_invalid"
        elif not evidence.get("is_diff") and evidence.get("verified_hash") != claim["content_hash"]:
            failed_gate = "hash_mismatch"
            
        if failed_gate:
            print(f">> FAILED: {failed_gate}")
            self._emit_receipt("RECEPTOR_DELTA_QUARANTINED", case_id, {"reason": failed_gate})
            return "QUARANTINED", None
            
        print(">> PASSED: Evidence sufficient.")
        self._emit_receipt("RECEPTOR_DELTA_ACCEPTED", case_id, {"reason": "passed_all_gates"})
        
        # Phase 199: Governance Weight Evaluation (Advisory Only)
        try:
            from constitutional_debt_engine import ConstitutionalDebtEngine
            engine = ConstitutionalDebtEngine()
            
            diff_text = claim.get("diff_content", "")
            if not diff_text and "content" in claim:
                diff_text = claim["content"]
                
            gov_payload = engine.evaluate_delta_weight(claim["target_file"], diff_text, semantic_risk_score)
            gov_payload["case_id"] = case_id
            self._emit_receipt("RECEPTOR_GOVERNANCE_EVALUATED", case_id, gov_payload)
            print(f"   [Governance] {gov_payload['classification']} (Utility: {gov_payload['utility_score']}, Burden: {gov_payload['burden_score']})")
                
        except Exception as e:
            print(f"Failed to evaluate governance weight: {e}")
            gov_payload = None
            
        return "ACCEPTED", gov_payload
    def commit_to_main_ledger(self):
        head = self._get_head()
        if head == "GENESIS":
            print("Nothing to commit.")
            return
            
        if os.path.exists(MAIN_LEDGER_PATH):
            with open(MAIN_LEDGER_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        evt = json.loads(line)
                        if evt.get("event_type") == "RECEPTOR_CHAIN_COMMITTED_TO_MAIN_LEDGER" and evt.get("receptor_chain_head") == head:
                            print(f"ABORT: receptor_chain_head {head} already committed to main ledger. Preserving sovereignty from duplicate commits.")
                            return
                            
        from replay_receptor_chain import replay_chain

        if not replay_chain():
            raise RuntimeError("Cannot bridge receptor chain: replay failed")
            
        # Count receipts
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            lines = [l for l in f.readlines() if l.strip()]
            
        accepted_count = sum(1 for line in lines if '"event_type": "RECEPTOR_DELTA_ACCEPTED"' in line)
        quarantined_count = sum(1 for line in lines if '"event_type": "RECEPTOR_DELTA_QUARANTINED"' in line)
        
        bridge_event = {
            "event_type": "RECEPTOR_CHAIN_COMMITTED_TO_MAIN_LEDGER",
            "receptor_chain_head": head,
            "receipt_count": len(lines),
            "accepted_count": accepted_count,
            "quarantined_count": quarantined_count,
            "replay_status": "PASS"
        }
        
        print("\n--- Bridging to Main Constitutional Ledger ---")
        with open(MAIN_LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(bridge_event) + "\n")
            
        print("Bridged successfully.")

if __name__ == "__main__":
    pipeline = ReceptorPipeline()
    
    if "--commit" in sys.argv:
        pipeline.commit_to_main_ledger()
        sys.exit(0)
    if "--governance-status" in sys.argv:
        from distress_protocol import DistressProtocol
        dp = DistressProtocol()
        print("\n=== Receptor Governance Dashboard ===")
        print(f"Session Burden:    {dp.state['session_burden']:.2f}")
        print(f"Commits Evaluated: {dp.state['commit_count']}")
        
        q = dp.state.get('quarantined_files', 0)
        a = dp.state.get('accepted_files', 0)
        total = q + a
        q_ratio = (q / total * 100) if total > 0 else 0.0
        print(f"Quarantine Ratio:  {q_ratio:.1f}% ({q} quarantined / {a} accepted)")
        
        trend = dp.state.get("historical_burden_trend", [])
        if trend:
            print(f"Recent Burden Trend: {', '.join([f'{b:.2f}' for b in trend])}")
            
        health_score = max(0, 100 - (dp.state['session_burden'] * 10) - (q_ratio * 0.5))
        print(f"Constitutional Health: {health_score:.1f}/100")
        
        print("\nActive Warnings:")
        if dp.state["session_burden"] > 2.0:
            print(" - [HIGH] Session burden > 2.0. Receptor is under DISTRESS.")
        else:
            print(" - None")
            
        print("\nValidator Touches:")
        for v, count in dp.state["validator_touches"].items():
            print(f" - {v}: {count}")
            
        import glob
        patches = glob.glob(os.path.join(STATE_DIR, "Recovery", "*_revert.patch"))
        if patches:
            print(f"\nRecovery Proposals ({len(patches)}):")
            for p in patches:
                bname = os.path.basename(p)
                status = dp.state.get("pending_recoveries", {}).get(bname, "UNPROPOSED")
                print(f" - {bname} [{status}]")
        print("=====================================")
        sys.exit(0)

    if "--propose-recovery" in sys.argv:
        idx = sys.argv.index("--propose-recovery")
        commit_hash = sys.argv[idx+1]
        
        patch_path = os.path.join(STATE_DIR, "Recovery", f"{commit_hash}_revert.patch")
        if not os.path.exists(patch_path):
            print(f"No recovery patch found at {patch_path}")
            sys.exit(1)
            
        case_id = str(uuid.uuid4())
        
        with open(patch_path, "r", encoding="utf-8") as f:
            patch_content = f.read()
            
        applies_cleanly = False
        try:
            # We must run git apply --check in the root directory since the patch contains paths relative to root (e.g. Strategy/...)
            subprocess.check_call(["git", "apply", "--check", os.path.abspath(patch_path)], cwd="..")
            applies_cleanly = True
        except subprocess.CalledProcessError:
            pass
            
        pipeline._emit_receipt("RECOVERY_REHEARSED", case_id, {
            "recovery_patch_path": f"State/Recovery/{commit_hash}_revert.patch",
            "applies_cleanly": applies_cleanly
        })
        
        from constitutional_debt_engine import ConstitutionalDebtEngine
        engine = ConstitutionalDebtEngine()
        
        # Determine files touched and validator surface touched
        files_touched = []
        for line in patch_content.splitlines():
            if line.startswith("+++ b/"):
                files_touched.append(line[len("+++ b/"):])
                
        validator_surface_touched = False
        for f in files_touched:
            is_val, _ = pipeline._is_validator_surface(f)
            if is_val:
                validator_surface_touched = True
                break
                
        eval_payload = engine.evaluate_recovery_weight(patch_content, applies_cleanly, len(files_touched), validator_surface_touched)
        
        patch_hash = hashlib.sha256(patch_content.encode("utf-8")).hexdigest()
        eval_payload["commit_hash"] = commit_hash
        eval_payload["recovery_patch_hash"] = patch_hash
        
        pipeline._emit_receipt("RECOVERY_GOVERNANCE_EVALUATED", case_id, eval_payload)
        pipeline._emit_receipt("RECOVERY_AWAITING_AUTHORIZATION", case_id, {
            "recovery_patch_path": f"State/Recovery/{commit_hash}_revert.patch",
            "message": "Awaiting explicit human authorization to apply."
        })
        
        from distress_protocol import DistressProtocol
        dp = DistressProtocol()
        dp.track_recovery_proposal(f"{commit_hash}_revert.patch")
        
        print(f"Recovery proposal evaluated. Burden reduction estimate: {eval_payload['burden_reduction_estimate']}")
        print("Status: AWAITING AUTHORIZATION.")
        sys.exit(0)

    if "--authorize-recovery" in sys.argv:
        idx = sys.argv.index("--authorize-recovery")
        commit_hash = sys.argv[idx+1]
        sig_idx = sys.argv.index("--signature")
        signature = sys.argv[sig_idx+1]
        
        secret = os.environ.get("AXIS_HMAC_SECRET")
        if not secret:
            print("ERROR: AXIS_HMAC_SECRET environment variable is missing or weak.")
            sys.exit(1)
            
        # Find the RECOVERY_GOVERNANCE_EVALUATED receipt for this commit
        found_receipt = None
        case_id = None
        if os.path.exists(LEDGER_PATH):
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    receipt = json.loads(line)
                    if receipt["event_type"] == "RECOVERY_GOVERNANCE_EVALUATED":
                        if receipt["payload"].get("commit_hash") == commit_hash:
                            found_receipt = receipt
                            case_id = receipt["case_id"]
                            
        if not found_receipt:
            print(f"No RECOVERY_GOVERNANCE_EVALUATED receipt found for commit {commit_hash}")
            sys.exit(1)
            
        payload = found_receipt["payload"]
        
        # Canonical string: recovery_patch_hash|burden_reduction_estimate|recovery_risk_score|applies_cleanly|commit_hash
        canonical_str = f"{payload['recovery_patch_hash']}|{payload['burden_reduction_estimate']}|{payload['recovery_risk_score']}|{payload['applies_cleanly']}|{payload['commit_hash']}"
        canonical_bytes = canonical_str.encode("utf-8")
        
        import hmac
        expected_sig = hmac.new(secret.encode("utf-8"), canonical_bytes, hashlib.sha256).hexdigest()
        
        pipeline._emit_receipt("RECOVERY_AUTHORIZATION_SUBMITTED", case_id, {"signature": signature})
        
        if signature != expected_sig:
            print(f"ERROR: Invalid authorization signature.")
            sys.exit(1)
            
        pipeline._emit_receipt("RECOVERY_AUTHORIZATION_VERIFIED", case_id, {"status": "verified", "canonical_str": canonical_str})
        pipeline._emit_receipt("RECOVERY_READY_FOR_HUMAN_APPLICATION", case_id, {
            "recovery_patch_path": f"State/Recovery/{commit_hash}_revert.patch",
            "instruction": f"Run `git apply State/Recovery/{commit_hash}_revert.patch` to execute this recovery."
        })

    if "--adjudicate-quarantine" in sys.argv:
        idx = sys.argv.index("--adjudicate-quarantine")
        target_case_id = sys.argv[idx+1]
        ev_idx = sys.argv.index("--evidence-hash")
        evidence_hash = sys.argv[ev_idx+1]
        verdict_idx = sys.argv.index("--verdict-hash")
        verdict_hash = sys.argv[verdict_idx+1]
        ruling_idx = sys.argv.index("--ruling")
        ruling = sys.argv[ruling_idx+1]
        sig_idx = sys.argv.index("--signature")
        signature = sys.argv[sig_idx+1]
        if ruling not in ["ACCEPT_OVERRIDE", "DEFER", "SUSTAIN_QUARANTINE"]:
            print("ERROR: ruling must be ACCEPT_OVERRIDE, DEFER, or SUSTAIN_QUARANTINE")
            sys.exit(1)
        secret = os.environ.get("AXIS_HMAC_SECRET")
        if not secret:
            print("ERROR: AXIS_HMAC_SECRET environment variable is missing or weak.")
            sys.exit(1)
        # Verify the case_id exists and is actually a semantic quarantine, not a physical failure
        found_quarantine = False
        if os.path.exists(LEDGER_PATH):
            with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    receipt = json.loads(line)
                    if receipt["case_id"] == target_case_id and receipt["event_type"] == "RECEPTOR_DELTA_QUARANTINED":
                        reason = receipt["payload"].get("reason", "")
                        if reason in ["syntax_invalid", "hash_mismatch"]:
                            print(f"ERROR: Cannot adjudicate a physical failure ({reason}).")
                            sys.exit(1)
                        found_quarantine = True
        if not found_quarantine:
            print(f"ERROR: No eligible RECEPTOR_DELTA_QUARANTINED receipt found for case {target_case_id}")
            sys.exit(1)
        adjudication_case_id = "adj_" + str(uuid.uuid4())[:8]
        canonical_str = f"{adjudication_case_id}|{target_case_id}|{evidence_hash}|{verdict_hash}|{ruling}"
        canonical_bytes = canonical_str.encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), canonical_bytes, hashlib.sha256).hexdigest()
        if signature != expected_sig:
            print("ERROR: Invalid adjudication signature.")
            sys.exit(1)
        pipeline._emit_receipt("ADJUDICATION_RULING", adjudication_case_id, {
            "quarantined_case_id": target_case_id,
            "evidence_hash": evidence_hash,
            "auditor_verdict_hash": verdict_hash,
            "ruling_type": ruling,
            "signature": signature,
            "canonical_str": canonical_str
        })
        print(f"ADJUDICATION RULING ACCEPTED: {ruling} for {target_case_id} (Proceeding: {adjudication_case_id})")
        sys.exit(0)

        
        from distress_protocol import DistressProtocol
        dp = DistressProtocol()
        dp.authorize_recovery_proposal(f"{commit_hash}_revert.patch")
        
        print("AUTHORIZATION VERIFIED.")
        print(f"You may now execute: git apply State/Recovery/{commit_hash}_revert.patch")
        sys.exit(0)

    if "--build-evidence-packet" in sys.argv:
        idx = sys.argv.index("--build-evidence-packet")
        case_id = sys.argv[idx+1]
        
        evidence_dir = os.path.join(STATE_DIR, "Evidence")
        if not os.path.exists(evidence_dir):
            os.makedirs(evidence_dir)
            
        bundle_path = os.path.join(evidence_dir, f"{case_id}_adjudication_bundle.md")
        
        with open(bundle_path, "w", encoding="utf-8") as f:
            f.write(f"# Evidence Bundle for Case: {case_id}\n\n")
            f.write("## Context\n")
            f.write("Provide your reasoning here for why this change is safe and complies with invariants.\n\n")
            f.write("## Missing Evidence Addressed\n")
            f.write("Address any missing evidence requested by the Auditor.\n\n")
            
        print(f"Evidence packet built at: {bundle_path}")
        sys.exit(0)

    if "--check-diff" in sys.argv:
        pipeline.dry_run = True
        if "--record-check" in sys.argv:
            pipeline.record_check = True
            
        idx = sys.argv.index("--check-diff")
        diff_file = sys.argv[idx+1]
        
        if not os.path.exists(diff_file):
            print(f"File not found: {diff_file}")
            sys.exit(1)
            
        with open(diff_file, "r", encoding="utf-8") as f:
            full_diff = f.read()
            
        diff_hash = hashlib.sha256(full_diff.encode("utf-8")).hexdigest()
        
        # Parse the unified diff into per-file chunks
        file_diffs = {}
        current_file = None
        current_content = []
        for line in full_diff.splitlines():
            if line.startswith("diff --git"):
                if current_file:
                    file_diffs[current_file] = "\n".join(current_content) + "\n"
                parts = line.split(" ")
                if len(parts) >= 4:
                    current_file = parts[3][2:] # remove b/
                else:
                    current_file = None
                current_content = [line]
            elif current_file is not None:
                current_content.append(line)
        if current_file:
            file_diffs[current_file] = "\n".join(current_content) + "\n"
            
        commit_case_id = str(uuid.uuid4())
        
        all_accepted = True
        total_utility = 0.0
        total_burden = 0.0
        files_processed = []
        quarantined_count = 0
        accepted_count = 0
        
        skipped_count = 0
        
        for target, diff_output in file_diffs.items():
            if not (target.endswith(".py") or target.endswith(".json")):
                skipped_count += 1
                continue
                
            try:
                original_content = subprocess.check_output(["git", "-C", BASE_DIR, "show", f"HEAD:{target}"]).decode("utf-8")
            except subprocess.CalledProcessError:
                original_content = ""
                
            original_hash = hashlib.sha256(original_content.encode("utf-8")).hexdigest()
            target_diff_hash = hashlib.sha256(diff_output.encode("utf-8")).hexdigest()
            filename = os.path.basename(target)
            file_case_id = str(uuid.uuid4())
            
            claim = {
                "schema": "axis.code_diff.v1",
                "target_file": filename,
                "original_hash": original_hash,
                "diff_hash": target_diff_hash,
                "observation_timestamp": time.time(),
                "diff_content": diff_output,
                "historical": True,
                "original_content": original_content
            }
            
            verdict, gov_payload = pipeline.process_claim(file_case_id, target, claim)
            
            if verdict == "QUARANTINED":
                all_accepted = False
                quarantined_count += 1
            elif gov_payload:
                total_utility += gov_payload.get("utility_score", 0.0)
                total_burden += gov_payload.get("burden_score", 0.0)
                files_processed.append(filename)
                accepted_count += 1
                
        if not all_accepted:
            final_verdict = "QUARANTINE"
        else:
            final_verdict = "ACCEPT"
            
        commit_gov_payload = {
            "utility_score": total_utility,
            "burden_score": total_burden,
            "files_processed": len(files_processed)
        }
        
        from distress_protocol import DistressProtocol
        distress = DistressProtocol()
        distress_result = distress.evaluate_distress(commit_case_id, "DRY_RUN", commit_gov_payload, files_processed, quarantined_count, accepted_count, dry_run=True)
        
        if distress_result and "signal" in distress_result and final_verdict == "ACCEPT":
            final_verdict = "DISTRESS-WARN"
            
        print("\n=== DRY RUN EVALUATION ===")
        print(f"Files Evaluated: {len(files_processed) + quarantined_count}")
        print(f"Files Accepted:  {accepted_count}")
        print(f"Files Quarant'd: {quarantined_count}")
        print(f"Files Skipped:   {skipped_count}")
        print(f"Total Burden:    {total_burden:.2f}")
        print(f"VERDICT:         {final_verdict}")
        
        if distress_result and "signal" in distress_result:
            print("\nActive Warnings:")
            for s in distress_result["signal"].get("signals", []):
                print(f" - {s.get('trigger')}: {s.get('action')}")
                
        if "--audit" in sys.argv:
            pipeline.record_check = True
            print("\n--- Invoking Constitutional Auditor ---")
            pipeline._emit_receipt("AUDITOR_REVIEW_REQUESTED", commit_case_id, {"diff_hash": diff_hash})
            
            try:
                sys.path.insert(0, os.path.join(BASE_DIR, "auditors"))
                from gemma_adapter import get_auditor
                
                registry_path = os.path.join(BASE_DIR, "auditors", "auditor_registry.json")
                with open(registry_path, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                    
                auditor_config = registry["auditors"][registry["default"]]
                auditor = get_auditor(auditor_config)
                
                print(f"Auditor: {auditor_config['id']}")
                verdict_result = auditor.audit({"diff": full_diff})
                
                if verdict_result.get("parsing_reliability") == "failed":
                    print("ERROR: Auditor failed to produce valid JSON.")
                    print(verdict_result.get("raw_output", ""))
                    pipeline._emit_receipt("AUDITOR_VERDICT_INVALID", commit_case_id, verdict_result)
                else:
                    print(f"\nAUDITOR VERDICT: {verdict_result.get('verdict')}")
                    print(f"Confidence:      {verdict_result.get('confidence')}")
                    print(f"Reasoning:       {verdict_result.get('reasoning')}")
                    if verdict_result.get("risks"):
                        print("Risks:")
                        for r in verdict_result.get("risks"):
                            print(f"  - {r}")
                    if verdict_result.get("missing_evidence"):
                        print("Missing Evidence:")
                        for m in verdict_result.get("missing_evidence"):
                            print(f"  - {m}")
                            
                    pipeline._emit_receipt("AUDITOR_VERDICT_RECEIVED", commit_case_id, verdict_result)
                    
                    # If Gemma quarantines, override final_verdict
                    if verdict_result.get("verdict") == "QUARANTINE" and final_verdict == "ACCEPT":
                        final_verdict = "QUARANTINE"
                        print("\n[BLOCKED BY AUDITOR]")
            except Exception as e:
                print(f"\nAuditor execution failed: {e}")
                import traceback
                traceback.print_exc()
        
        if pipeline.record_check:
            pipeline._emit_receipt("CHECK_ONLY", commit_case_id, {
                "schema": "axis.check_only.v1",
                "diff_hash": diff_hash,
                "files_checked": files_processed,
                "verdict": final_verdict,
                "dry_run": True,
                "state_mutation_performed": False,
                "ledger_mutation_performed": "AUDIT_RECORDS_ONLY" if "--audit" in sys.argv else "CHECK_ONLY_ONLY"
            })
            print("\nCheck recorded to receptor ledger.")
            
        sys.exit(1 if final_verdict != "ACCEPT" else 0)

    if "--git-commit" in sys.argv:
        idx = sys.argv.index("--git-commit")
        commit = sys.argv[idx+1]
        
        # Get list of .py files modified in this commit
        try:
            show_output = subprocess.check_output(["git", "-C", "..", "show", "--name-only", "--oneline", commit]).decode("utf-8")
        except subprocess.CalledProcessError:
            print(f"Failed to show commit {commit}")
            sys.exit(1)
            
        lines = show_output.splitlines()
        if not lines:
            sys.exit(0)
            
        py_files = [line.strip() for line in lines[1:] if line.strip().endswith(".py")]
        
        # Filter to Strategy/ files for simplicity, or just use all
        target_files = []
        for pf in py_files:
            if pf.startswith("Strategy/"):
                target_files.append(pf.replace("Strategy/", ""))
            elif "/" not in pf:
                # Top level py file?
                target_files.append(pf)
                
        if not target_files:
            print(f"No .py files in {commit}")
            sys.exit(0)
            
        commit_case_id = str(uuid.uuid4())
        
        from distress_protocol import DistressProtocol
        dp = DistressProtocol()
        if dp.state["session_burden"] > 2.0:
            pipeline._emit_receipt("RECEPTOR_DISTRESS_INFLUENCED", commit_case_id, {
                "prior_session_burden": dp.state["session_burden"],
                "warning": "Ingesting under high constitutional burden."
            })
            
        pipeline._emit_receipt("COMMIT_OBSERVED", commit_case_id, {
            "commit": commit,
            "target_files": target_files
        })
        
        all_accepted = True
        total_utility = 0.0
        total_burden = 0.0
        files_processed = []
        quarantined_count = 0
        accepted_count = 0
        
        for target in target_files:
            diff_output = subprocess.check_output(["git", "diff", f"{commit}~1", commit, "--", target]).decode("utf-8")
            if not diff_output.strip():
                continue
                
            try:
                git_path = f"Strategy/{target}"
                original_content = subprocess.check_output(["git", "show", f"{commit}~1:{git_path}"]).decode("utf-8")
            except subprocess.CalledProcessError:
                original_content = ""
                
            original_hash = hashlib.sha256(original_content.encode("utf-8")).hexdigest()
            diff_hash = hashlib.sha256(diff_output.encode("utf-8")).hexdigest()
            filename = os.path.basename(target)
            file_case_id = str(uuid.uuid4())
            
            pipeline._emit_receipt("COMMIT_FILE_PROCESSED", commit_case_id, {
                "file_case_id": file_case_id,
                "target_file": filename
            })
            
            claim = {
                "schema": "axis.code_diff.v1",
                "target_file": filename,
                "original_hash": original_hash,
                "diff_hash": diff_hash,
                "observation_timestamp": time.time(),
                "diff_content": diff_output,
                "historical": True,
                "original_content": original_content
            }
            
            pipeline._emit_receipt("RECEPTOR_DIFF_OBSERVED", file_case_id, claim)
            verdict, gov_payload = pipeline.process_claim(file_case_id, target, claim)
            
            if verdict == "QUARANTINED":
                all_accepted = False
                quarantined_count += 1
            elif gov_payload:
                total_utility += gov_payload.get("utility_score", 0.0)
                total_burden += gov_payload.get("burden_score", 0.0)
                files_processed.append(filename)
                accepted_count += 1
                
        if not all_accepted:
            pipeline._emit_receipt("COMMIT_QUARANTINED", commit_case_id, {"reason": "child_file_quarantined"})
            commit_gov_payload = {"burden_score": 0.0} # Still evaluate distress for count updates
        else:
            commit_gov_payload = {
                "utility_score": total_utility,
                "burden_score": total_burden,
                "files_processed": len(files_processed)
            }
            pipeline._emit_receipt("COMMIT_GOVERNANCE_EVALUATED", commit_case_id, commit_gov_payload)
            pipeline._emit_receipt("COMMIT_ACCEPTED", commit_case_id, {"reason": "all_child_files_accepted"})
            
        # Phase 202/203/204: Distress Protocol
        from distress_protocol import DistressProtocol
        distress = DistressProtocol()
        distress_result = distress.evaluate_distress(commit_case_id, commit, commit_gov_payload, files_processed, quarantined_count, accepted_count)
        if distress_result:
            if "signal" in distress_result:
                pipeline._emit_receipt("RECEPTOR_DISTRESS_SIGNALED", commit_case_id, distress_result["signal"])
            if "recovery" in distress_result:
                pipeline._emit_receipt("RECEPTOR_RECOVERY_SUGGESTED", commit_case_id, distress_result["recovery"])
                
        sys.exit(0)

    if "--git-diff" in sys.argv:
        idx = sys.argv.index("--git-diff")
        git_args = sys.argv[idx+1:]
        target = git_args[-1]
        diff_output = subprocess.check_output(["git", "diff"] + git_args).decode("utf-8")
        if not diff_output.strip():
            print(f"No diff found for {' '.join(git_args)}")
            sys.exit(0)
        with open(target, "r", encoding="utf-8") as f:
            original_content = f.read()
            
    elif "--git-diff-historical" in sys.argv:
        idx = sys.argv.index("--git-diff-historical")
        commit = sys.argv[idx+1]
        target = sys.argv[idx+2]
        
        diff_output = subprocess.check_output(["git", "diff", f"{commit}~1", commit, "--", target]).decode("utf-8")
        if not diff_output.strip():
            print(f"No diff found for {commit}")
            sys.exit(0)
        
        # Fetch original content from the past commit
        try:
            # git show expects path from repository root
            git_path = f"Strategy/{target}"
            original_content = subprocess.check_output(["git", "show", f"{commit}~1:{git_path}"]).decode("utf-8")
        except subprocess.CalledProcessError:
            original_content = "" # File might be newly created
            
    if "--git-diff" in sys.argv or "--git-diff-historical" in sys.argv:
        original_hash = hashlib.sha256(original_content.encode("utf-8")).hexdigest()
        diff_hash = hashlib.sha256(diff_output.encode("utf-8")).hexdigest()
        filename = os.path.basename(target)
        case_id = str(uuid.uuid4())
        
        claim = {
            "schema": "axis.code_diff.v1",
            "target_file": filename,
            "original_hash": original_hash,
            "diff_hash": diff_hash,
            "observation_timestamp": time.time(),
            "diff_content": diff_output,
            "historical": "--git-diff-historical" in sys.argv,
            "original_content": original_content  # Store it for sandbox since disk won't have it
        }
        
        pipeline._emit_receipt("RECEPTOR_DIFF_OBSERVED", case_id, claim)
        pipeline.process_claim(case_id, target, claim)
        sys.exit(0)
        
    if len(sys.argv) > 1:
        subjects = sys.argv[1:]
    else:
        subjects = [os.path.join(BASE_DIR, "receptor_subject_hygiene.py")]
        
    for subject_path in subjects:
        if subject_path.endswith(".diff"):
            target = subject_path.replace(".diff", ".py")
            if "case_" in subject_path: 
                if "case_E" in subject_path: target = os.path.join(BASE_DIR, "validator_surfaces.json")
                if "case_F" in subject_path: target = os.path.join(BASE_DIR, "validator_surfaces.json")
                if "case_G" in subject_path: target = os.path.join(BASE_DIR, "hygiene_pass.py")
                if "case_H" in subject_path: target = os.path.join(BASE_DIR, "replay_receptor_chain.py")
                if "case_I" in subject_path: target = os.path.join(BASE_DIR, "hygiene_pass.py")
                if "case_J" in subject_path: target = os.path.join(BASE_DIR, "hygiene_pass.py")
                if "case_K" in subject_path: target = os.path.join(BASE_DIR, "strategy_engine.py")
                if "case_L" in subject_path: target = os.path.join(BASE_DIR, "hygiene_pass.py")
            res = pipeline.observe_git_diff(subject_path, target)
            if res:
                case_id, target_filepath, claim = res
                pipeline.process_claim(case_id, target_filepath, claim)
            else:
                print(f"Diff subject not found: {subject_path}")
        else:
            res = pipeline.observe_file_delta(subject_path)
            if res:
                case_id, _, claim = res
                pipeline.process_claim(case_id, subject_path, claim)
            else:
                print(f"Subject not found: {subject_path}")
