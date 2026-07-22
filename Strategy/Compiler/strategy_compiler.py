import os
import json
import hashlib
import shutil
import urllib.request
from datetime import datetime, timezone

LEDGER_PATH = r"D:\Infinite\Infinity\Strategy\Strategy_Ledger.jsonl"
APPROVED_PATH = r"D:\Infinite\Infinity\Strategy\Approvals\Strategy_Approved.jsonl"
STATE_PATH = r"D:\Infinite\Infinity\Strategy\State\strategy_state.json"
ORACLE_POLICY = r"D:\Infinite\Infinity\Strategy\Compiler\oracle_policy.v1.json"
OVERLAY_DIR = r"D:\Infinite\Infinity\Runtime\Decision\Overlays"
STATE_API = "http://127.0.0.1:8025/state"

class StrategyCompiler:
    def __init__(self):
        self.state = self._load_state()
        self.policy = self._load_policy()
        self.objective_policy_path = os.path.join(os.path.dirname(STATE_PATH), "..", r"Compiler\objective_policy.v1.json")
        self.objective_policy = self._load_objective_policy()

    def _load_state(self):
        if not os.path.exists(STATE_PATH):
            return {"compiler_last_offset": 0, "active_overlays": {}}
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "active_overlays" not in data:
                data["active_overlays"] = {}
            return data

    def _save_state(self):
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def _load_policy(self):
        if not os.path.exists(ORACLE_POLICY):
            return {}
        with open(ORACLE_POLICY, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_objective_policy(self):
        if not os.path.exists(self.objective_policy_path):
            return {}
        with open(self.objective_policy_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _fetch_metrics(self):
        try:
            with urllib.request.urlopen(STATE_API, timeout=5) as response:
                state = json.loads(response.read().decode("utf-8"))
                return state.get("governance_metrics", {}), state
        except Exception as e:
            print(f"Failed to fetch metrics for regression check: {e}")
            return None, None

    def evaluate_ledger(self):
        # 1. Check for regressions and no-benefit rollbacks before processing new proposals
        self.check_regressions()

        if not os.path.exists(LEDGER_PATH):
            return

        new_offset = self.state.get("compiler_last_offset", 0)
        
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            f.seek(new_offset)
            lines = f.readlines()
            new_offset = f.tell()

        for line in lines:
            if not line.strip():
                continue
            try:
                proposal = json.loads(line)
                oracle = proposal.get("oracle", {})
                
                if oracle.get("decision") == "auto_approved":
                    self._apply_proposal(proposal)
                    
            except Exception as e:
                print(f"Error processing proposal line: {e}")

        self.state["compiler_last_offset"] = new_offset
        self.state["compiler_last_run_utc"] = datetime.now(timezone.utc).isoformat()
        self._save_state()

    def check_regressions(self):
        guard = self.policy.get("overlay_guard", {})
        obj_eval = self.objective_policy.get("evaluation_parameters", {})
        
        metrics, full_state = self._fetch_metrics()
        if not metrics:
            return

        now = datetime.now(timezone.utc)
        window = guard.get("verification_window_sec", 1800)
        rules = guard.get("regression_metrics", {})

        for art_type, info in list(self.state.get("active_overlays", {}).items()):
            if info.get("status") != "applied":
                continue

            last_applied = datetime.fromisoformat(info["last_applied_utc"])
            delta_sec = (now - last_applied).total_seconds()
            
            # 1. Immediate Regression Check (within window)
            if delta_sec <= window and guard.get("rollback_on_regression"):
                regression_reason = None
                
                # Stability Drop
                baseline_stability = info.get("baseline_stability", 100)
                current_stability = metrics.get("stability_index", 100)
                if baseline_stability - current_stability >= rules.get("stability_drop_threshold", 20):
                    regression_reason = f"stability_drop:{baseline_stability}->{current_stability}"

                # Metrics Health
                health = full_state.get("metrics_health", "healthy")
                if health in rules.get("deny_metrics_health", []):
                    regression_reason = f"bad_health:{health}"

                # Progress Stalled
                if rules.get("deny_progress_stalled") and metrics.get("progress_stalled"):
                    regression_reason = "progress_stalled"

                # Time Anomalies
                if rules.get("deny_time_anomalies") and metrics.get("time_anomalies"):
                    regression_reason = "time_anomalies_detected"

                if regression_reason:
                    print(f"REGRESSION DETECTED for {art_type}: {regression_reason}. Rolling back.")
                    self._rollback(art_type, regression_reason)
                    continue

            # 2. Causality Window & No-Benefit Check (after window passes)
            if delta_sec > obj_eval.get("min_observation_window_sec", 3600) and info.get("evaluation"):
                eval_data = info.get("evaluation")
                target_metric_name = eval_data.get("metric") # e.g. mttr_p95_24h
                
                # Retrieve current metric value
                # For MTTR, we look in mttr_inputs or directly in metrics
                cur_val = None
                if target_metric_name == "mttr_p95_24h":
                    cur_val = metrics.get("mttr_inputs", {}).get("p95")
                else:
                    cur_val = metrics.get(target_metric_name)
                    
                if cur_val is not None:
                    baseline = eval_data.get("baseline")
                    expected_delta = eval_data.get("expected_delta", 0)
                    success_band = eval_data.get("success_band", {}).get("improve_by_at_least", 0)
                    
                    # If expected delta is negative (minimizing), improvement is baseline - cur_val
                    # Otherwise cur_val - baseline
                    actual_delta = baseline - cur_val if expected_delta < 0 else cur_val - baseline
                    
                    if actual_delta < success_band:
                        print(f"NO BENEFIT DETECTED for {art_type}: Predicted {expected_delta}, got {actual_delta}. Rolling back.")
                        self._rollback(art_type, f"no_benefit:{actual_delta}<{success_band}")
                    else:
                        print(f"Improvement Verified for {art_type}: {actual_delta} >= {success_band}.")
                        # Clear evaluation to stop checking
                        info["evaluation_verified"] = True
                        del info["evaluation"]

    def _apply_proposal(self, proposal):
        proposed_change = proposal.get("proposed_change", {})
        artifact_path = proposed_change.get("proposed_artifact_path")
        artifact_type = proposed_change.get("artifact_type")
        proposal_id = proposal.get("proposal_id")
        evaluation = proposal.get("evaluation")
        
        if not artifact_path or not os.path.exists(artifact_path):
            print(f"Artifact not found: {artifact_path}")
            return

        # Two-Phase Commit
        overlay_target = os.path.join(OVERLAY_DIR, f"{artifact_type}.current.json")
        candidate_target = os.path.join(OVERLAY_DIR, f"{artifact_type}.candidate.json")
        
        try:
            # Phase 1: Write Candidate
            shutil.copy2(artifact_path, candidate_target)
            
            # Validation: Ensure it's valid JSON
            with open(candidate_target, "r", encoding="utf-8") as f:
                json.load(f)
            
            # Phase 2: Atomic Rename
            metrics, _ = self._fetch_metrics()
            baseline_stability = metrics.get("stability_index", 100) if metrics else 100
            
            os.replace(candidate_target, overlay_target)
            
            # Update state
            prev_info = self.state["active_overlays"].get(artifact_type, {})
            self.state["active_overlays"][artifact_type] = {
                "current_id": proposal_id,
                "previous_id": prev_info.get("current_id"),
                "last_applied_utc": datetime.now(timezone.utc).isoformat(),
                "baseline_stability": baseline_stability,
                "status": "applied",
                "evaluation": evaluation
            }
            
            # Log Approval
            self._log_approval(proposal_id, "applied", artifact_type, artifact_path)
            print(f"Applied proposal {proposal_id} to {overlay_target}")

        except Exception as e:
            print(f"Failed to apply proposal {proposal_id}: {e}")
            if os.path.exists(candidate_target):
                os.remove(candidate_target)

    def _rollback(self, artifact_type, reason):
        info = self.state["active_overlays"].get(artifact_type)
        if not info or not info.get("previous_id"):
            print(f"Cannot rollback {artifact_type}: no previous_id found.")
            overlay_target = os.path.join(OVERLAY_DIR, f"{artifact_type}.current.json")
            if os.path.exists(overlay_target):
                os.remove(overlay_target)
            info["status"] = "rolled_back_to_baseline"
        else:
            overlay_target = os.path.join(OVERLAY_DIR, f"{artifact_type}.current.json")
            if os.path.exists(overlay_target):
                os.remove(overlay_target)
            info["status"] = "rolled_back"
            
        info["rollback_utc"] = datetime.now(timezone.utc).isoformat()
        info["rollback_reason"] = reason
        
        # Log Rollback
        rollback_entry = {
            "ts_utc": info["rollback_utc"],
            "proposal_id": info.get("current_id"),
            "status": "rolled_back",
            "reason": reason,
            "artifact_type": artifact_type
        }
        with open(APPROVED_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rollback_entry) + "\n")
        
        self._save_state()

    def _log_approval(self, proposal_id, status, artifact_type, artifact_path):
        approval_entry = {
            "ts_utc": datetime.now(timezone.utc).isoformat(),
            "proposal_id": proposal_id,
            "status": status,
            "artifact_type": artifact_type,
            "artifact_path": artifact_path
        }
        with open(APPROVED_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(approval_entry) + "\n")

if __name__ == '__main__':
    compiler = StrategyCompiler()
    compiler.evaluate_ledger()
