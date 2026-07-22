import os
import json
from collections import Counter
from typing import Dict, List, Any

class ReplayEngine:
    """
    Phase 2: Deterministic Audit Reproduction.
    This engine sequentially replays every logged receipt from a designated sealed baseline
    to prove that the current runtime is strictly derivable from its ledger history.
    
    First version focuses on mapping where derivability breaks, not pretending full replay exists.
    """
    
    def __init__(self, strategy_dir: str):
        self.strategy_dir = strategy_dir
        self.witness_ledger_path = os.path.join(strategy_dir, "State", "forensic_witness_ledger.jsonl")
        self.archive_dir = os.path.join(strategy_dir, "State", "Archival_Exports")
        self.state_file = os.path.join(strategy_dir, "State", "strategy_state.json")
        self.anchor_file = os.path.join(strategy_dir, "State", "calibration_continuity_anchor.json")
        
    def load_witness_records(self) -> List[Dict]:
        records = []
        # Sort archives assuming naming convention forensic_witness_ledger_*.jsonl
        paths = []
        if os.path.exists(self.archive_dir):
            for f in sorted(os.listdir(self.archive_dir)):
                if f.startswith("forensic_witness_ledger_"):
                    paths.append(os.path.join(self.archive_dir, f))
        paths.append(self.witness_ledger_path)
        
        for path in paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8-sig') as f:
                    for line in f:
                        if line.strip():
                            try:
                                records.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
        return records

    def execute_replay(self) -> Dict:
        """
        Executes the deterministic replay.
        Returns a classification report mapping gaps and successes.
        """
        records = self.load_witness_records()
        
        boundaries = {}
        replay_segments_dir = os.path.join(self.strategy_dir, "State", "ReplaySegments")
        if os.path.exists(replay_segments_dir):
            for f in os.listdir(replay_segments_dir):
                if f.startswith("segment_boundary_") and f.endswith(".json"):
                    try:
                        with open(os.path.join(replay_segments_dir, f), "r") as bf:
                            bdata = json.load(bf)
                            if "cycle" in bdata:
                                boundaries[bdata["cycle"]] = bdata
                    except Exception:
                        pass
        
        event_counts = Counter()
        classifications = Counter()
        divergences = []
        unsupported = set()
        mutation_events = []
        
        first_cycle = None
        last_cycle = None
        
        expected_prev = "none"
        if records:
            expected_prev = records[0].get("prev_witness_hash", "none")

        reanchor_segments = []
        current_segment = {"start_cycle": None, "end_cycle": None, "record_count": 0, "start_index": 0}

        for idx, record in enumerate(records):
            event_type = record.get("event_type", "unknown")
            cycle = record.get("cycle", 0)
            if first_cycle is None:
                first_cycle = cycle
            last_cycle = cycle
            
            if current_segment["start_cycle"] is None:
                current_segment["start_cycle"] = cycle
            
            event_counts[event_type] += 1
            
            prev_hash = record.get("prev_witness_hash", "none")
            curr_hash = record.get("witness_hash", "none")
            
            # 1. Check Spine
            if prev_hash != expected_prev and expected_prev != "none":
                reason = "Chain Break"
                if cycle in boundaries:
                    reason = "operator_segment_boundary"
                    
                divergences.append({
                    "record_index": idx,
                    "cycle": cycle,
                    "event_type": event_type,
                    "expected_prev": expected_prev,
                    "actual_prev": prev_hash,
                    "reason": reason
                })
                reanchor_segments.append(current_segment)
                current_segment = {"start_cycle": cycle, "end_cycle": cycle, "record_count": 1, "start_index": idx}
            else:
                current_segment["record_count"] += 1
                current_segment["end_cycle"] = cycle
            
            expected_prev = curr_hash
            
            # 2. Classification
            classification = "unknown"
            if event_type in ["ECOSYSTEM_CYCLE_COMPLETE", "cycle_verdict", "sovereign_arbitration"]:
                classification = "replayable_transition"
            elif event_type in ["calibration_update:ontological_health", "ecosystem_observation_emitted", "trust_state_violation", "semantic_registry_audit"]:
                classification = "metadata_only"
            elif event_type in ["CANDIDATE_QUARANTINED", "self_improvement_applied"]:
                classification = "mutation_receipt"
                mutation_events.append(record)
            elif event_type == "CODE_REFACTOR_APPLIED":
                data = record.get("data", {})
                reason = record.get("reason", "")
                
                # Extract payload fields from the new strict contract
                pre_hash = data.get("pre_hash")
                post_hash = data.get("post_hash")
                proposal_id = data.get("proposal_id") or data.get("mutation_id")
                artifacts_dir = data.get("artifact_folder")
                approval_receipt_id = data.get("approval_receipt_id")
                
                has_all_fields = bool(pre_hash and post_hash and proposal_id and artifacts_dir and approval_receipt_id)
                
                if not has_all_fields:
                    classification = "mutation_missing_artifacts"
                else:
                    abs_artifacts_dir = artifacts_dir
                    if not os.path.isabs(abs_artifacts_dir):
                        abs_artifacts_dir = os.path.join(self.strategy_dir, artifacts_dir)

                    # Import axis_crypto_helpers explicitly from Strategy dir
                    import sys
                    strategy_dir = r"D:\Infinite\Infinity\Strategy"
                    if strategy_dir not in sys.path:
                        sys.path.append(strategy_dir)
                    try:
                        from axis_crypto_helpers import _hash_file_stream
                    except ImportError as e:
                        raise RuntimeError(f"hash_helper_import_failed: {e}")

                    receipt_path = os.path.join(abs_artifacts_dir, "receipt.json")
                    pre_file = os.path.join(abs_artifacts_dir, "pre_file.py")
                    trial_file = os.path.join(abs_artifacts_dir, "trial_file.py")
                    patch_file = os.path.join(abs_artifacts_dir, "patch.diff")
                    approval_file = os.path.join(abs_artifacts_dir, "approval.json")
                    test_result_file = os.path.join(abs_artifacts_dir, "test_result.json")

                    missing_files = []
                    for p in [receipt_path, pre_file, trial_file, patch_file, approval_file, test_result_file]:
                        if not os.path.exists(p):
                            missing_files.append(p)
                    
                    if missing_files:
                        classification = "mutation_missing_artifacts"
                    else:
                        try:
                            # Recompute hashes using the exact domain
                            actual_pre_hash = _hash_file_stream(pre_file, "refactor_target")[:16]
                            actual_trial_hash = _hash_file_stream(trial_file, "refactor_target")[:16]
                            
                            with open(receipt_path, "r") as f:
                                receipt_data = json.load(f)
                            
                            with open(test_result_file, "r") as f:
                                test_data = json.load(f)
                            
                            with open(approval_file, "r") as f:
                                approval_data = json.load(f)

                            patch_size = os.path.getsize(patch_file)

                            if actual_pre_hash != pre_hash[:16]:
                                classification = "mutation_hash_mismatch"
                            elif actual_trial_hash != post_hash[:16]:
                                classification = "mutation_hash_mismatch"
                            elif patch_size == 0:
                                classification = "mutation_hash_mismatch"
                            elif test_data.get("status") != "pass":
                                classification = "mutation_hash_mismatch"
                            elif approval_data.get("approval_receipt_id") != approval_receipt_id:
                                classification = "mutation_hash_mismatch"
                            else:
                                classification = "mutation_replayable"
                                mutation_events.append(record)

                        except Exception as e:
                            classification = "mutation_missing_artifacts"
            elif event_type in ["fatal_error"]:
                classification = "non_deterministic"
            else:
                classification = "unsupported"
                unsupported.add(event_type)
            
            classifications[classification] += 1

        reanchor_segments.append(current_segment)
        final_tail = expected_prev
        
        # Load state and anchor
        ledger_head = "unknown"
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                data = json.load(f)
                state = data.get("mission_shadow_v2", data)
                ledger_head = state.get("witness_chain_head", "unknown")
                
        anchor_head = "unknown"
        if os.path.exists(self.anchor_file):
            with open(self.anchor_file, "r") as f:
                anchor = json.load(f)
                anchor_head = anchor.get("witness_chain_head", "unknown")

        # Pass 3: Gap Report
        total = len(records)
        replayable = classifications.get("replayable_transition", 0) + classifications.get("metadata_only", 0)
        percentage = (replayable / total * 100) if total > 0 else 0.0
        
        spine_valid = len(divergences) == 0
        tail_matches_anchor = (final_tail == ledger_head == anchor_head)
        
        # Explicitly compute active_segment_valid
        # The final segment is valid if no chain breaks occurred within its index range
        active_segment_valid = True
        last_seg = reanchor_segments[-1]
        for div in divergences:
            if div["record_index"] > last_seg["start_index"]:
                active_segment_valid = False
                break
        
        # Also double check that expected_prev is fully linked to the end
        if last_seg["record_count"] > 0:
            last_record = records[-1]
            if final_tail != last_record.get("witness_hash"):
                active_segment_valid = False
        
        report = {
            "total_records": total,
            "first_cycle": first_cycle,
            "last_cycle": last_cycle,
            "final_tail": final_tail,
            "ledger_head": ledger_head,
            "anchor_head": anchor_head,
            "tail_matches_anchor": tail_matches_anchor,
            "spine_valid": spine_valid,
            "breakpoint_count": len(divergences),
            "reanchor_segments": reanchor_segments,
            "active_segment_valid": active_segment_valid,
            "classifications": dict(classifications),
            "event_counts": dict(event_counts),
            "exact_breakpoints": divergences,
            "unsupported_event_types": list(unsupported),
            "mutation_events_requiring_artifact_replay": len(mutation_events),
            "percentage_replayable_at_spine_level": f"{percentage:.2f}%",
            "recommendation_for_next_replay_target": "CODE_REFACTOR_APPLIED" if mutation_events else "ECOSYSTEM_CYCLE_COMPLETE"
        }
        
        return report

if __name__ == "__main__":
    engine = ReplayEngine(r"D:\Infinite\Infinity\Strategy")
    results = engine.execute_replay()
    print(json.dumps(results, indent=4))
