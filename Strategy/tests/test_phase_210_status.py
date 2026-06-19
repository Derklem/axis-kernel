import os
import sys
import unittest
import json
import hashlib
import tempfile
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from ledger_reader import parse_ledger_fast

class TestConsoleStatus(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.ledger_path = os.path.join(self.test_dir, "test_ledger.jsonl")
        self.head = "GENESIS"
        self.timestamp = 1000000.0

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _emit(self, event_type, case_id, payload):
        payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        self.timestamp += 1.0

        receipt_base = f"{event_type}|{case_id}|{self.head}|{payload_hash}|{self.timestamp}"
        receipt_hash = hashlib.sha256(receipt_base.encode("utf-8")).hexdigest()

        receipt = {
            "case_id": case_id,
            "event_type": event_type,
            "parent_receptor_head": self.head,
            "payload": payload,
            "payload_hash": payload_hash,
            "receipt_hash": receipt_hash,
            "timestamp": self.timestamp
        }

        self.head = receipt_hash

        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(receipt) + "\n")

    def test_metrics_computation(self):
        case_1 = "case_1_accept"
        self._emit("RECEPTOR_OBSERVATION_RECORDED", case_1, {"target_file": "a.py"})
        self._emit("RECEPTOR_DELTA_ACCEPTED", case_1, {})
        self._emit("RECEPTOR_GOVERNANCE_EVALUATED", case_1, {"burdens": {"complexity": 5.0}})

        case_2 = "case_2_quarantine"
        self._emit("RECEPTOR_OBSERVATION_RECORDED", case_2, {"target_file": "b.py"})
        self._emit("RECEPTOR_DELTA_QUARANTINED", case_2, {"reason": "risk"})

        case_3 = "case_3_adjudicated"
        self._emit("RECEPTOR_OBSERVATION_RECORDED", case_3, {"target_file": "c.py"})
        self._emit("RECEPTOR_DELTA_QUARANTINED", case_3, {"reason": "risk"})
        self._emit("ADJUDICATION_RULING", case_3, {"ruling_type": "ACCEPT_OVERRIDE"})

        self._emit("AUDITOR_REVIEW_REQUESTED", case_2, {})

        cases, metrics, receipts = parse_ledger_fast(self.ledger_path)

        self.assertEqual(metrics["accepted"], 1)
        self.assertEqual(metrics["quarantined"], 2)  # Total quaternines emitted
        self.assertEqual(metrics["overrides"], 1)
        self.assertEqual(metrics["audit_requests"], 1)
        self.assertEqual(metrics["session_burden"], 5.0)

        # Simulating console.py's open_quarantine_count
        open_quarantine_count = 0
        for cid, case in cases.items():
            events = case.get("events", [])
            if "RECEPTOR_DELTA_QUARANTINED" in events and "ADJUDICATION_RULING" not in events:
                open_quarantine_count += 1

        self.assertEqual(open_quarantine_count, 1)

        # Debt Score: (1 * 10) + (1 * 5) + 5.0 = 20.0
        score = (open_quarantine_count * 10) + (metrics["overrides"] * 5) + metrics["session_burden"]
        self.assertEqual(score, 20.0)

if __name__ == "__main__":
    unittest.main()
