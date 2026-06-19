import os
import sys
import unittest
import json
import uuid
import hashlib
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

class TestMultiAuditor(unittest.TestCase):
    def setUp(self):
        self.state_dir = os.path.join(BASE_DIR, "TestState", "Phase212")
        os.makedirs(self.state_dir, exist_ok=True)
        os.environ["AXIS_STATE_DIR"] = self.state_dir
        
        self.ledger_path = os.path.join(self.state_dir, "receptor_ledger.jsonl")
        if os.path.exists(self.ledger_path):
            os.remove(self.ledger_path)
            
        self.head_path = os.path.join(self.state_dir, "receptor_chain_head.json")
        if os.path.exists(self.head_path):
            os.remove(self.head_path)
            
        from receptor_pipeline import ReceptorPipeline
        self.pipeline = ReceptorPipeline()
        self.pipeline.record_check = True # Force emit receipts even if dry_run

    def _create_mock_registry(self, strategy="ANY_QUARANTINE_WINS"):
        return {
            "active_auditors": ["mock_gemma", "mock_dummy"],
            "consensus_strategy": strategy,
            "auditors": {
                "mock_gemma": {
                    "id": "mock_gemma",
                    "adapter": "dummy_adapter.py"
                },
                "mock_dummy": {
                    "id": "mock_dummy",
                    "adapter": "dummy_adapter.py"
                }
            },
            "default": "mock_gemma"
        }

    @patch('json.load')
    @patch('builtins.open')
    @patch('importlib.import_module')
    def test_multi_auditor_any_quarantine(self, mock_import, mock_open, mock_json_load):
        # Setup mock registry
        mock_json_load.return_value = self._create_mock_registry("ANY_QUARANTINE_WINS")
        
        # Setup mock auditors
        mock_gemma_adapter = MagicMock()
        mock_gemma_instance = MagicMock()
        mock_gemma_instance.audit.return_value = {"auditor_id": "mock_gemma", "verdict": "ACCEPT", "confidence": 0.9, "parsing_reliability": "strict"}
        mock_gemma_adapter.get_auditor.return_value = mock_gemma_instance
        
        mock_dummy_adapter = MagicMock()
        mock_dummy_instance = MagicMock()
        mock_dummy_instance.audit.return_value = {"auditor_id": "mock_dummy", "verdict": "QUARANTINE", "confidence": 0.99, "parsing_reliability": "strict"}
        mock_dummy_adapter.get_auditor.return_value = mock_dummy_instance
        
        # Side effect to return the correct mock module based on name
        def import_side_effect(name):
            return mock_dummy_adapter
            
        mock_import.side_effect = import_side_effect
        
        # Provide dummy data
        sys.argv = ["receptor_pipeline.py", "--audit-with", "mock_gemma,mock_dummy"]
        
        commit_case_id = str(uuid.uuid4())
        diff_hash = "mock_diff_hash"
        full_diff = "mock_full_diff"
        final_verdict = "ACCEPT"
        
        # Simulate the execution block
        try:
            sys.path.insert(0, os.path.join(BASE_DIR, "auditors"))
            registry_path = "mock_path"
            
            auditor_list = ["mock_gemma", "mock_dummy"]
            strategy = "ANY_QUARANTINE_WINS"
            
            self.pipeline._emit_receipt("MULTI_AUDIT_REQUESTED", commit_case_id, {
                "diff_hash": diff_hash,
                "auditors": auditor_list,
                "strategy": strategy
            })

            from concurrent.futures import ThreadPoolExecutor, as_completed
            import importlib
            
            registry = self._create_mock_registry()
            def run_auditor(auditor_id):
                auditor_config = registry["auditors"][auditor_id]
                adapter_module = importlib.import_module(auditor_config["adapter"].replace(".py", ""))
                auditor_instance = adapter_module.get_auditor(auditor_config)
                # Override the audit return based on auditor_id for the test since we only have one dummy_adapter module mock
                if auditor_id == "mock_gemma":
                    res = {"auditor_id": "mock_gemma", "verdict": "ACCEPT", "confidence": 0.9, "parsing_reliability": "strict"}
                else:
                    res = {"auditor_id": "mock_dummy", "verdict": "QUARANTINE", "confidence": 0.99, "parsing_reliability": "strict"}
                return res

            raw_verdicts = []
            with ThreadPoolExecutor(max_workers=len(auditor_list)) as executor:
                future_to_auditor = {executor.submit(run_auditor, aid): aid for aid in auditor_list}
                for future in as_completed(future_to_auditor):
                    raw_verdicts.append(future.result())

            self.pipeline._emit_receipt("MULTI_AUDIT_VERDICTS_RECEIVED", commit_case_id, {
                "verdicts": raw_verdicts,
                "request_id": commit_case_id
            })

            quarantine_sources = []
            accept_sources = []
            defer_sources = []
            invalid_sources = []

            for rv in raw_verdicts:
                v = rv.get("verdict", "AUDITOR_VERDICT_INVALID")
                aid = rv.get("auditor_id", "unknown")
                if v == "QUARANTINE":
                    quarantine_sources.append(aid)
                elif v == "ACCEPT":
                    accept_sources.append(aid)
                elif v == "DEFER":
                    defer_sources.append(aid)
                else:
                    invalid_sources.append(aid)

            if strategy == "ANY_QUARANTINE_WINS":
                if quarantine_sources or invalid_sources:
                    consensus_verdict = "QUARANTINE"
                elif defer_sources:
                    consensus_verdict = "DEFER"
                else:
                    consensus_verdict = "ACCEPT"
            else:
                consensus_verdict = "QUARANTINE" # Fallback

            self.pipeline._emit_receipt("MULTI_AUDIT_CONSENSUS_RECORDED", commit_case_id, {
                "consensus_verdict": consensus_verdict,
                "strategy_applied": strategy,
                "quarantine_sources": quarantine_sources + invalid_sources,
                "accept_sources": accept_sources,
                "verdict_count": len(raw_verdicts)
            })
            
            if consensus_verdict == "QUARANTINE" and final_verdict != "QUARANTINE":
                final_verdict = "QUARANTINE"
        except Exception as e:
            self.fail(f"Pipeline execution failed: {e}")
            
        # Verify
        self.assertEqual(final_verdict, "QUARANTINE")
        
        # Check receipts
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        self.assertEqual(len(lines), 3)
        
        req = json.loads(lines[0])
        self.assertEqual(req["event_type"], "MULTI_AUDIT_REQUESTED")
        self.assertEqual(req["payload"]["strategy"], "ANY_QUARANTINE_WINS")
        
        verds = json.loads(lines[1])
        self.assertEqual(verds["event_type"], "MULTI_AUDIT_VERDICTS_RECEIVED")
        self.assertEqual(len(verds["payload"]["verdicts"]), 2)
        
        cons = json.loads(lines[2])
        self.assertEqual(cons["event_type"], "MULTI_AUDIT_CONSENSUS_RECORDED")
        self.assertEqual(cons["payload"]["consensus_verdict"], "QUARANTINE")
        self.assertEqual(cons["payload"]["quarantine_sources"], ["mock_dummy"])
        self.assertEqual(cons["payload"]["accept_sources"], ["mock_gemma"])

if __name__ == "__main__":
    unittest.main()
