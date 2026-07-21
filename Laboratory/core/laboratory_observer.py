import os
import sys
import json
import datetime
import glob
import argparse

def count_files(directory, pattern="*.json"):
    path = os.path.join(directory, pattern)
    return len(glob.glob(path))

def count_by_status(directory, status_field="status", target_status="passed"):
    count = 0
    pattern = os.path.join(directory, "*.json")
    for filepath in glob.glob(pattern):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                if data.get(status_field) == target_status:
                    count += 1
        except Exception:
            pass
    return count

def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, choices=["empirical", "governance"], default="empirical")
    args = parser.parse_args()
        
    base_dir = r"D:\Mind"
    obs_dir = os.path.join(base_dir, "Laboratory", "observations")
    os.makedirs(obs_dir, exist_ok=True)
    
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now_utc.strftime("%Y%m%d_%H%M%S")
    now_iso = now_utc.isoformat()
    
    pointer_path = os.path.join(base_dir, "Laboratory", "config", "current_policy.json")
    epoch_id = "unknown"
    active_policy_version = "unknown"
    active_policy_snapshot = {}
    
    try:
        if os.path.exists(pointer_path):
            with open(pointer_path, 'r', encoding='utf-8') as f:
                pointer = json.load(f)
                epoch_id = pointer.get("epoch", "unknown")
                active_policy_version = pointer.get("active_version", "unknown")
                policy_path = os.path.join(os.path.dirname(pointer_path), pointer.get("path", ""))
                if os.path.exists(policy_path):
                    with open(policy_path, 'r', encoding='utf-8') as pf:
                        active_policy_snapshot = json.load(pf)
    except:
        pass
        
    obs_data = {
        "id": f"LAB_OBS_{timestamp}",
        "observer_version": f"lab_observer_v2_{args.mode}",
        "active_epoch": epoch_id,
        "active_policy_version": active_policy_version,
        "active_policy_snapshot": active_policy_snapshot,
        "created_utc": now_iso,
        "observation_window": {
            "start": now_iso,
            "end": now_iso
        }
    }
    
    if args.mode == "empirical":
        experiments = []
        exp_dir = os.path.join(base_dir, "EventStore", "experiments")
        if os.path.exists(exp_dir):
            for fp in glob.glob(os.path.join(exp_dir, "*.json")):
                exp = load_json(fp)
                if exp: experiments.append(exp)
                
        resolved = [e for e in experiments if e.get("status", "").startswith("resolved_")]
        pending = [e for e in experiments if e.get("status") == "pending"]
        
        total_conf = 0.0
        correct_count = 0
        for e in resolved:
            total_conf += e.get("confidence", 0.0)
            if e.get("status") == "resolved_correct":
                correct_count += 1
                
        avg_confidence = round(total_conf / len(resolved), 4) if resolved else 0.0
        actual_success_rate = round(correct_count / len(resolved), 4) if resolved else 0.0
        calibration_error = round(abs(avg_confidence - actual_success_rate), 4)
        
        total_latency = 0.0
        total_decision_latency = 0.0
        decision_actuated_count = 0
        
        for e in resolved:
            try:
                start = datetime.datetime.fromisoformat(e.get("start_date"))
                end = datetime.datetime.fromisoformat(e.get("resolution_date"))
                days = (end - start).total_seconds() / 86400.0
                total_latency += days
            except:
                pass
                
            if "decision_date" in e and "first_action_date" in e:
                try:
                    dec = datetime.datetime.fromisoformat(e.get("decision_date"))
                    act = datetime.datetime.fromisoformat(e.get("first_action_date"))
                    minutes = (act - dec).total_seconds() / 60.0
                    total_decision_latency += minutes
                    decision_actuated_count += 1
                except:
                    pass
                    
        avg_latency_days = round(total_latency / len(resolved), 2) if resolved else 0.0
        avg_decision_latency_minutes = round(total_decision_latency / decision_actuated_count, 2) if decision_actuated_count else 0.0
        
        surprises = [e for e in resolved if e.get("surprise") and len(str(e.get("surprise")).strip()) > 3]
        surprise_rate = round(len(surprises) / len(resolved), 4) if resolved else 0.0
        
        recent_resolved = 0
        for e in resolved:
            try:
                end = datetime.datetime.fromisoformat(e.get("resolution_date"))
                if (now_utc - end).total_seconds() <= (7 * 86400):
                    recent_resolved += 1
            except:
                pass
                
        valued = [e for e in resolved if e.get("value_capture") and len(str(e.get("value_capture")).strip()) > 3]
        value_capture_rate = round(len(valued) / len(resolved), 4) if resolved else 0.0
        
        info_gain = [e for e in resolved if e.get("information_gain") is True]
        information_gain_rate = round(len(info_gain) / len(resolved), 4) if resolved else 0.0
        
        obs_data["empirical_metrics"] = {
            "total_experiments_pending": len(pending),
            "total_experiments_resolved": len(resolved),
            "weekly_throughput": recent_resolved,
            "average_confidence": avg_confidence,
            "actual_success_rate": actual_success_rate,
            "calibration_error": calibration_error,
            "average_resolution_latency_days": avg_latency_days,
            "average_decision_latency_minutes": avg_decision_latency_minutes,
            "surprise_rate": surprise_rate,
            "value_capture_rate": value_capture_rate,
            "information_gain_rate": information_gain_rate
        }
        
    elif args.mode == "governance":
        hypotheses_active = count_files(os.path.join(base_dir, "Hypotheses", "active"))
        designs_pending = count_files(os.path.join(base_dir, "Predictions", "pending"))
        designs_approved = count_files(os.path.join(base_dir, "Predictions", "approved"))
        sandbox_results = count_files(os.path.join(base_dir, "Laboratory", "sandbox_results"))
        evaluations = count_files(os.path.join(base_dir, "Evaluations"))
        belief_updates_pending = count_files(os.path.join(base_dir, "BeliefUpdates", "pending"))
        belief_updates_approved = count_files(os.path.join(base_dir, "BeliefUpdates", "approved"))
        mutation_receipts = count_files(os.path.join(base_dir, "MutationReceipts"))
        
        audit_passed = count_by_status(os.path.join(base_dir, "MutationAudits"), target_status="passed")
        audit_failed = count_by_status(os.path.join(base_dir, "MutationAudits"), target_status="failed")
        chain_passed = count_by_status(os.path.join(base_dir, "ChainVerifications"), target_status="passed")
        chain_failed = count_by_status(os.path.join(base_dir, "ChainVerifications"), target_status="failed")
        
        total_audits = audit_passed + audit_failed
        audit_success_rate = round(audit_passed / total_audits, 4) if total_audits > 0 else 1.0
        
        total_chains = chain_passed + chain_failed
        chain_integrity_rate = round(chain_passed / total_chains, 4) if total_chains > 0 else 1.0
        
        obs_data["counts"] = {
            "hypotheses_active": hypotheses_active,
            "experimental_designs_pending": designs_pending,
            "approved_experiments": designs_approved,
            "sandbox_results": sandbox_results,
            "evaluations": evaluations,
            "belief_updates_pending": belief_updates_pending,
            "belief_updates_approved": belief_updates_approved,
            "mutation_receipts": mutation_receipts,
            "mutation_audits_passed": audit_passed,
            "mutation_audits_failed": audit_failed,
            "chain_verifications_passed": chain_passed,
            "chain_verifications_failed": chain_failed
        }
        obs_data["health_metrics"] = {
            "audit_success_rate": audit_success_rate,
            "chain_integrity_rate": chain_integrity_rate,
            "fixture_contamination_rate": 0.0
        }
        obs_data["protocol_overhead"] = {
            "artifacts_per_completed_chain": 0
        }
        obs_data["temporal_trends"] = {
            "preserved_uncertainty_rate": 0.0
        }
        obs_data["notes"] = [
            "The observer must never infer missing meaning. It counts artifacts and computes simple ratios only."
        ]
    
    output_path = os.path.join(obs_dir, f"LAB_OBS_{timestamp}.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(obs_data, f, indent=2)
        
    print(f"Observation Logged: {output_path}")

if __name__ == "__main__":
    main()
