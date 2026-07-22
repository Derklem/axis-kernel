import os
import sys
import json
import hashlib
import py_compile
import subprocess
import time
import uuid

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
        basename = os.path.basename(filename)
        surfaces = self._get_validator_surfaces()
        for pattern in surfaces.keys():
            if fnmatch.fnmatch(basename, pattern):
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
            return "QUARANTINED"
        
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
                
                # Sandbox it
                case_sandbox = os.path.join(SANDBOX_DIR, case_id)
                os.makedirs(case_sandbox, exist_ok=True)
                trial_path = os.path.join(case_sandbox, claim["target_file"])
                
                with open(trial_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                    
                self._emit_receipt("RECEPTOR_DIFF_SANDBOXED", case_id, {"sandbox_path": trial_path})
                
                py_compile.compile(trial_path, doraise=True)
                evidence["syntax_valid"] = True
                
                trial_hash = hashlib.sha256(new_content.encode("utf-8")).hexdigest()
                evidence["verified_hash"] = trial_hash
                evidence["is_diff"] = True
                
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
            return "QUARANTINED"
            
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
            
            if gov_payload["burden_score"] > 0.7:
                print("   [!] DISTRESS SIGNAL: High Governance Burden Detected")
                self._emit_receipt("RECEPTOR_DISTRESS_SIGNALED", case_id, {"burden_score": gov_payload["burden_score"]})
                
        except Exception as e:
            print(f"Failed to evaluate governance weight: {e}")
            
        return "ACCEPTED"
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
