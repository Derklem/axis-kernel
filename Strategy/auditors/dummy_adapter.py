import os
from base_auditor import BaseAuditor

class DummyAdapter(BaseAuditor):
    def audit(self, payload):
        verdict = os.environ.get("DUMMY_VERDICT", "QUARANTINE")
        
        return {
            "auditor_id": self.auditor_id,
            "verdict": verdict,
            "confidence": 0.99,
            "risks": ["Dummy risk identified for testing."],
            "missing_evidence": ["Missing dummy evidence."],
            "rationale": f"Dummy adapter is hardcoded to return {verdict}.",
            "parsing_reliability": "strict"
        }

def get_auditor(config):
    return DummyAdapter(config)
    

