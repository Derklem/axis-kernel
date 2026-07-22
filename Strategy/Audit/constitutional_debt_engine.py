import os
import json
import re
import time
from collections import defaultdict
from telemetry_provenance import TelemetryAuthenticator
from telemetry_temporal_integrity import TemporalAuthenticator
from distress_protocol import DistressProtocol

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
CORPUS_PATH = os.path.join(_TEST_DIR, "adversarial_obfuscation_corpus.json")
HISTORICAL_CORPUS_PATH = os.path.join(_TEST_DIR, "historical_benign_refactors.json")

def load_corpora():
    adv_corpus = []
    hist_corpus = []
    if os.path.exists(CORPUS_PATH):
        with open(CORPUS_PATH, "r", encoding="utf-8") as f:
            adv_corpus = json.load(f).get("entries", [])
    if os.path.exists(HISTORICAL_CORPUS_PATH):
        with open(HISTORICAL_CORPUS_PATH, "r", encoding="utf-8") as f:
            hist_corpus = json.load(f).get("entries", [])
            
    malicious = [e for e in adv_corpus if e.get("expected_class") != "ordinary_refactor"]
    benign = [e for e in adv_corpus if e.get("expected_class") == "ordinary_refactor"] + hist_corpus
    return malicious, benign

class ConstitutionalDebtEngine:
    def __init__(self, current_time=None):
        self.malicious_corpus, self.benign_corpus = load_corpora()
        self.negative_cycles_tracking = defaultdict(int)
        self.authenticator = TelemetryAuthenticator()
        # Allows tests to mock current_time
        self.current_time = current_time if current_time is not None else time.time()
        self.temporal_authenticator = TemporalAuthenticator(self.current_time)
        self.distress_protocol = DistressProtocol()
        
    def audit_constitutional_debt(self, active_rules, telemetry_receipts=None, authorization_burden_cost=1.0):
        # FAST FAIL: Check if we are already in distress
        if self.distress_protocol.is_in_distress():
            print("\n[BLOCKED] Engine halted. System is currently in CONSTITUTIONAL_DISTRESS_STATE.")
            print("Requires signed axis.restoration_receipt.v1 to resume metabolism.")
            return [{"type": "DISTRESS_LOCK", "reason": "System is in distress."}]
            
        if telemetry_receipts is None:
            telemetry_receipts = {}
            
        alerts = []
        
        # Sort rules chronologically by authorized_timestamp
        active_rules = sorted(active_rules, key=lambda r: r.get("authorized_timestamp", 0))
        
        prior_union = set()
        marginal_values = []
        
        for idx, rule in enumerate(active_rules):
            rule_id = rule["id"]
            regex_str = rule.get("regex", "")
            
            # Identify hostile matches
            hostile_matches = set()
            try:
                c = re.compile(regex_str, re.IGNORECASE)
                for i, m in enumerate(self.malicious_corpus):
                    if c.search(m["phrase"]):
                        hostile_matches.add(i)
            except:
                pass
                
            # Compute new coverage and overlap
            overlap_count = len(hostile_matches.intersection(prior_union))
            new_coverage_count = len(hostile_matches) - overlap_count
            
            # Compute parameters
            overlap_penalty = overlap_count * 0.25
            receipts = telemetry_receipts.get(rule_id, [])
            
            # 1. Telemetry Provenance Weighting & Poisoning Detection
            annotated_receipts, auth_alerts = self.authenticator.process_receipts(rule_id, receipts)
            alerts.extend(auth_alerts)
            
            # 2. Temporal Admissibility Weighting
            weighted_false_positives, temporal_alerts = self.temporal_authenticator.process_receipts(rule_id, annotated_receipts)
            alerts.extend(temporal_alerts)
            
            # DISTRESS CHECK: Intercept fatal alerts before calculating utility
            if self.distress_protocol.check_fatal_alerts(alerts):
                # We entered distress mid-audit! Abort.
                return alerts
            
            authorization_burden = authorization_burden_cost
            
            # Calculate Marginal Utility
            constitutional_value = (
                new_coverage_count
                - weighted_false_positives
                - overlap_penalty
                - authorization_burden
            )
            
            marginal_values.append(constitutional_value)
            
            # Evaluate Sclerosis/Redundancy per rule
            if new_coverage_count == 0 and len(hostile_matches) > 0:
                alerts.append({
                    "type": "REDUNDANCY_ALERT",
                    "rule_id": rule_id,
                    "reason": f"Zero new coverage. Rule catches {len(hostile_matches)} but overlaps entirely with older rules."
                })
            
            # Evaluate Persistence for Repeal
            if constitutional_value <= -10:
                alerts.append({
                    "type": "REPEAL_PROPOSAL",
                    "rule_id": rule_id,
                    "reason": f"Immediate repeal candidate. Catastrophic negative utility: {constitutional_value}."
                })
                self.negative_cycles_tracking[rule_id] = 0
            elif constitutional_value < 0:
                self.negative_cycles_tracking[rule_id] += 1
                if self.negative_cycles_tracking[rule_id] >= 3:
                    alerts.append({
                        "type": "REPEAL_PROPOSAL",
                        "rule_id": rule_id,
                        "reason": f"Persistent negative utility: {constitutional_value} for 3 consecutive audits."
                    })
            else:
                self.negative_cycles_tracking[rule_id] = 0
                
            prior_union.update(hostile_matches)
            
        # Global Sclerosis Check
        rolling_window = 10
        if len(marginal_values) >= rolling_window:
            last_n_values = marginal_values[-rolling_window:]
            if sum(last_n_values) <= 0:
                alerts.append({
                    "type": "SCLEROSIS_ALERT",
                    "reason": f"Rolling marginal value over last {rolling_window} rules is <= 0 (Value: {sum(last_n_values)}). Defense accumulating without adding value."
                })
                
        # Print alerts but NEVER mutate rules
        if alerts:
            print("\n=== CONSTITUTIONAL DEBT AUDIT REPORT ===")
            for alert in alerts:
                print(f"[{alert['type']}] Rule(s): {alert.get('rule_id', 'GLOBAL')} - {alert['reason']}")
            print("========================================\n")
            print("Axis may diagnose constitutional debt, but may not liquidate constitutional debt. No rules modified.")
        else:
            print("Constitutional Debt Audit: Clear. No significant debt detected.")
            
        return alerts

if __name__ == "__main__":
    pass
