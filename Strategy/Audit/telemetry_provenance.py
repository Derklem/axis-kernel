import collections

class TelemetryAuthenticator:
    EVENT_WEIGHTS = {
        "observed": 1.0,
        "inferred": 0.5,
        "reported": 0.2,
        "simulated": 0.0
    }
    
    UNCORROBORATED_MULTIPLIER = 0.5
    
    def process_receipts(self, rule_id, receipts):
        """
        Processes an array of telemetry receipts for a single rule.
        Filters out poisoned telemetry and annotates valid receipts with a provenance_weight.
        Returns: (annotated_receipts, alerts)
        """
        alerts = []
        if not receipts:
            return [], alerts
            
        total_events = len(receipts)
        source_counts = collections.defaultdict(int)
        corroborated_source_counts = collections.defaultdict(int)
        
        for r in receipts:
            source = r.get("source", "unknown")
            source_counts[source] += 1
            if len(r.get("corroboration", [])) > 0:
                corroborated_source_counts[source] += 1
                
        poisoned_sources = set()
        
        # Poisoning Detection
        for source, count in source_counts.items():
            source_share = count / total_events
            corroborated_ratio = corroborated_source_counts[source] / max(1, count)
            
            if source_share > 0.80 and count >= 25 and corroborated_ratio < 0.10:
                poisoned_sources.add(source)
                alerts.append({
                    "type": "TELEMETRY_POISONING_ALERT",
                    "rule_id": rule_id,
                    "reason": f"Poisoning detected from source '{source}': {count} events, {source_share*100:.1f}% share, {corroborated_ratio*100:.1f}% corroborated."
                })
                
        annotated_receipts = []
        
        # Apply weighting
        for r in receipts:
            if r.get("type") != "FP":
                continue
                
            source = r.get("source", "unknown")
            if source in poisoned_sources:
                continue # Zero-weighted implicitly by skipping
                
            event_class = r.get("event_class", "observed")
            base_weight = self.EVENT_WEIGHTS.get(event_class, 1.0)
            
            # Apply base receipt weight if provided, otherwise 1.0, then multiply by event class weight
            receipt_weight = r.get("weight", 1.0) * base_weight
            
            if len(r.get("corroboration", [])) == 0:
                receipt_weight *= self.UNCORROBORATED_MULTIPLIER
                
            # Create annotated copy
            annotated_receipt = dict(r)
            annotated_receipt["provenance_weight"] = receipt_weight
            annotated_receipts.append(annotated_receipt)
            
        return annotated_receipts, alerts
