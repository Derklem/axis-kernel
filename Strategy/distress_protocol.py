import os
import json
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = os.environ.get("AXIS_STATE_DIR", os.path.join(BASE_DIR, "State"))
STATE_FILE = os.path.join(STATE_DIR, "distress_state.json")

class DistressProtocol:
    def __init__(self):
        self.state = self._load_state()

    def _load_state(self):
        state = {
            "session_burden": 0.0,
            "commit_count": 0,
            "validator_touches": {},
            "pending_recoveries": {},
            "quarantined_files": 0,
            "accepted_files": 0,
            "historical_burden_trend": []
        }
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                state.update(loaded)
        return state

    def authorize_recovery_proposal(self, patch_path):
        if "pending_recoveries" not in self.state:
            self.state["pending_recoveries"] = {}
        self.state["pending_recoveries"][patch_path] = "AUTHORIZED"
        self._save_state()

    def track_recovery_proposal(self, patch_path):
        if "pending_recoveries" not in self.state:
            self.state["pending_recoveries"] = {}
        self.state["pending_recoveries"][patch_path] = "AWAITING_AUTHORIZATION"
        self._save_state()

    def _save_state(self):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=4)

    def evaluate_distress(self, commit_case_id, commit_hash, gov_payload, files_processed, quarantined_count=0, accepted_count=0, dry_run=False):
        import subprocess
        import hashlib
        burden = gov_payload.get("burden_score", 0.0)
        
        # Update state
        self.state["session_burden"] += burden
        self.state["commit_count"] += 1
        self.state["quarantined_files"] = self.state.get("quarantined_files", 0) + quarantined_count
        self.state["accepted_files"] = self.state.get("accepted_files", 0) + accepted_count
        
        if "historical_burden_trend" not in self.state:
            self.state["historical_burden_trend"] = []
        self.state["historical_burden_trend"].append(burden)
        if len(self.state["historical_burden_trend"]) > 10:
            self.state["historical_burden_trend"] = self.state["historical_burden_trend"][-10:]
        
        
        for f in files_processed:
            if "validator_surfaces.json" in f or "replay_receptor_chain.py" in f or "distress_protocol.py" in f or "receptor_pipeline.py" in f:
                self.state["validator_touches"][f] = self.state["validator_touches"].get(f, 0) + 1
                
        if not dry_run:
            self._save_state()

        signals = []
        recovery_receipt = None
        
        # 1. Single commit burden > 0.75
        if burden > 0.75:
            # Generate reverse patch
            patch_dir = os.path.join(BASE_DIR, "State", "Recovery")
            os.makedirs(patch_dir, exist_ok=True)
            patch_path = os.path.join(patch_dir, f"{commit_hash}_revert.patch")
            
            try:
                # We need files relative to root for git diff
                git_files = [f"Strategy/{f}" for f in files_processed]
                patch_content = subprocess.check_output(["git", "-C", "..", "diff", "-R", f"{commit_hash}~1", commit_hash, "--"] + git_files).decode("utf-8")
                
                with open(patch_path, "w", encoding="utf-8") as f:
                    f.write(patch_content)
                    
                patch_hash = hashlib.sha256(patch_content.encode("utf-8")).hexdigest()
                recovery_receipt = {
                    "recovery_patch_path": f"State/Recovery/{commit_hash}_revert.patch",
                    "recovery_patch_hash": patch_hash,
                    "recommended_action": "review_revert_patch"
                }
            except Exception as e:
                print(f"Failed to generate reverse patch: {e}")
                
            signals.append({
                "severity": "high",
                "trigger": "single_commit_burden_exceeded",
                "burden": burden,
                "action": "review_commit"
            })
            
        # 2. Session burden > 2.0
        if self.state["session_burden"] > 2.0:
            signals.append({
                "severity": "high",
                "trigger": "session_burden_exceeded",
                "cumulative_burden": self.state["session_burden"],
                "action": "audit_session"
            })
            
        # 3. Repeated validator touches
        for vf, count in self.state["validator_touches"].items():
            if count >= 2:
                signals.append({
                    "severity": "medium",
                    "trigger": "repeated_validator_touches",
                    "file": vf,
                    "count": count,
                    "action": "audit_validator_modifications"
                })
                
        result = {}
        if signals:
            result["signal"] = {
                "schema": "axis.distress_signal.v1",
                "commit_id": commit_case_id,
                "signals": signals
            }
        if recovery_receipt:
            result["recovery"] = recovery_receipt
            
        return result if result else None

