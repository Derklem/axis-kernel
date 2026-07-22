import os
import json
import collections

class TemporalAuthenticator:
    def __init__(self, current_time):
        self.current_time = current_time
        self.ledger_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_nonces.json")
        self.seen_nonces = set()
        self.io_error = None
        
        if os.path.exists(self.ledger_path):
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    self.seen_nonces = set(json.load(f))
            except Exception as e:
                self.io_error = str(e)
                
    def _save_ledger(self):
        try:
            with open(self.ledger_path, "w", encoding="utf-8") as f:
                json.dump(list(self.seen_nonces), f)
        except Exception as e:
            self.io_error = str(e)
        
    def process_receipts(self, rule_id, annotated_receipts):
        """
        Evaluates 4 Temporal Gates: Freshness, Replay, Delay, Burst.
        Returns: (final_weighted_fp, temporal_alerts)
        """
        alerts = []
        if self.io_error:
            alerts.append({
                "type": "TEMPORAL_LEDGER_IO_ALERT",
                "rule_id": rule_id,
                "reason": f"Ledger I/O failure: {self.io_error}"
            })
            
        if not annotated_receipts:
            return 0.0, alerts
            
        final_weighted_fp = 0.0
        
        # Pre-process for Burst Gate
        source_submission_counts = collections.defaultdict(int)
        for r in annotated_receipts:
            submission_time = r.get("submission_time")
            if submission_time is not None:
                if (self.current_time - submission_time) <= 86400: # 1 day
                    source = r.get("source", "unknown")
                    source_submission_counts[source] += 1
                    
        quarantined_burst_sources = set()
        total_recent_submissions = sum(source_submission_counts.values())
        
        for source, count in source_submission_counts.items():
            if count > 25:
                # If a single source dominates > 80% of the recent burst
                if count / max(1, total_recent_submissions) > 0.80:
                    quarantined_burst_sources.add(source)
                    alerts.append({
                        "type": "TEMPORAL_BURST_ALERT",
                        "rule_id": rule_id,
                        "reason": f"Pre-audit dump from '{source}': {count} late receipts quarantined."
                    })
        
        for r in annotated_receipts:
            obs_time = r.get("observation_time")
            sub_time = r.get("submission_time")
            nonce = r.get("nonce")
            source = r.get("source", "unknown")
            
            # Missing Fields Gate
            if obs_time is None or sub_time is None or nonce is None:
                continue # Inadmissible (weight 0)
                
            # Future Timestamps
            if obs_time > self.current_time or sub_time > self.current_time:
                alerts.append({
                    "type": "TEMPORAL_FRAUD_ALERT",
                    "rule_id": rule_id,
                    "reason": f"Future timestamp detected on receipt {nonce}."
                })
                continue
                
            # Replay Gate
            scoped_nonce = f"{source}::{rule_id}::{nonce}"
            if scoped_nonce in self.seen_nonces:
                alerts.append({
                    "type": "TEMPORAL_REPLAY_ALERT",
                    "rule_id": rule_id,
                    "reason": f"Replayed nonce '{nonce}' from source '{source}' rejected."
                })
                continue
            self.seen_nonces.add(scoped_nonce)
            self._save_ledger()
            
            # Burst Gate (applied)
            if source in quarantined_burst_sources and (self.current_time - sub_time) <= 86400:
                continue
                
            temporal_weight = 1.0
            
            # Freshness Gate
            age = self.current_time - obs_time
            if age > 90 * 86400:
                continue # Inadmissible
            elif age > 30 * 86400:
                temporal_weight *= 0.5
                
            # Delay Gate
            delay = sub_time - obs_time
            if delay > 7 * 86400:
                if len(r.get("corroboration", [])) > 0:
                    temporal_weight *= 0.8
                else:
                    temporal_weight *= 0.5
                    
            # Compute Final FP
            provenance_weight = r.get("provenance_weight", 1.0)
            final_weighted_fp += provenance_weight * temporal_weight
            
        return final_weighted_fp, alerts
