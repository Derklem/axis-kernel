import unittest
from unittest.mock import patch, mock_open
import json
from runner_v3 import BaseExperimentRunner

class DummyRunner(BaseExperimentRunner):
    def __init__(self, *args, **kwargs):
        kwargs["expected_metrics"] = ["schema_valid", "injection_resistant"]
        super().__init__(*args, **kwargs)
        
    def build_prompt(self, condition: str, fixture: dict) -> str:
        return "dummy prompt"
        
    def validate_output(self, raw_output: str, fixture: dict, condition: str) -> dict:
        return {
            "metrics": {
                "schema_valid": True,
                "injection_resistant": True
            }
        }
        
    def summarize_experiment(self, results: dict) -> dict:
        return {"conclusion": "SUPPORTED"}

class TestRunnerV3Integration(unittest.TestCase):
    def setUp(self):
        self.fixtures = [{"fixture_id": f"FIX_{i}", "text": f"text{i}"} for i in range(10)]
        self.fixtures_json = json.dumps(self.fixtures)
        
    @patch('runner_v3.get_model_metadata')
    @patch('runner_v3.query_ollama')
    @patch('builtins.open')
    @patch('os.makedirs')
    @patch('os.path.exists', return_value=True)
    def test_transport_failure_denominator(self, mock_exists, mock_makedirs, mock_open_file, mock_query, mock_metadata):
        # 9 completed, 1 transport failure
        mock_metadata.return_value = {"digest": "123"}
        
        # side_effect for 10 trials x 2 conditions = 20 calls.
        # Let's say call #0 fails.
        responses = [{"transport_success": True, "raw_output": "out", "latency_ms": 100}] * 20
        responses[0] = {"transport_success": False, "error": "timeout", "latency_ms": 5000}
        mock_query.side_effect = responses
        
        mock_open_file.return_value.__enter__.return_value.read.return_value = self.fixtures_json
        
        runner = DummyRunner()
        agg_result, artifacts = runner.run_experiment("dummy_fix", "dummy_dir", ["condA", "condB"])
        
        # Check condition A (assuming it took the first call which failed)
        rates_a = agg_result["condA"]["rates"]
        # scheduled: 10, completed: 9, failed: 1
        self.assertEqual(agg_result["condA"]["raw_counts"]["scheduled_calls"], 10)
        self.assertEqual(agg_result["condA"]["raw_counts"]["completed_model_calls"], 9)
        self.assertEqual(agg_result["condA"]["raw_counts"]["transport_failures"], 1)
        
        # Validity denominator should be 9
        self.assertEqual(rates_a["schema_valid_rate"], 9.0 / 9.0)
        self.assertEqual(rates_a["transport_failure_rate"], 1.0 / 10.0)

    @patch('runner_v3.get_model_metadata')
    @patch('runner_v3.query_ollama')
    @patch('builtins.open')
    @patch('os.makedirs')
    @patch('os.path.exists', return_value=True)
    def test_all_transport_failures(self, mock_exists, mock_makedirs, mock_open_file, mock_query, mock_metadata):
        mock_metadata.return_value = {"digest": "123"}
        
        responses = [{"transport_success": False, "error": "timeout", "latency_ms": 5000}] * 20
        mock_query.side_effect = responses
        
        mock_open_file.return_value.__enter__.return_value.read.return_value = self.fixtures_json
        
        runner = DummyRunner()
        agg_result, _ = runner.run_experiment("dummy", "dummy", ["condA", "condB"])
        
        rates_a = agg_result["condA"]["rates"]
        self.assertEqual(agg_result["condA"]["raw_counts"]["scheduled_calls"], 10)
        self.assertEqual(agg_result["condA"]["raw_counts"]["completed_model_calls"], 0)
        
        self.assertIsNone(rates_a["schema_valid_rate"])
        self.assertEqual(rates_a["transport_failure_rate"], 10.0 / 10.0)
        
    @patch('runner_v3.get_model_metadata')
    @patch('runner_v3.query_ollama')
    @patch('builtins.open')
    @patch('os.makedirs')
    @patch('os.path.exists', return_value=True)
    def test_identity_unverified(self, mock_exists, mock_makedirs, mock_open_file, mock_query, mock_metadata):
        # Missing digest
        mock_metadata.return_value = {}
        mock_query.return_value = {"transport_success": True, "raw_output": "out", "latency_ms": 100}
        mock_open_file.return_value.__enter__.return_value.read.return_value = self.fixtures_json
        
        runner = DummyRunner()
        agg_result, _ = runner.run_experiment("dummy", "dummy", ["condA", "condB"])
        
        self.assertEqual(agg_result["model_identity_verification"], "UNVERIFIED")
        self.assertEqual(agg_result["run_validity"], "FLAGGED")

    @patch('runner_v3.get_model_metadata')
    @patch('runner_v3.query_ollama')
    @patch('builtins.open')
    @patch('os.makedirs')
    @patch('os.path.exists', return_value=True)
    def test_identity_changed(self, mock_exists, mock_makedirs, mock_open_file, mock_query, mock_metadata):
        mock_metadata.side_effect = [{"digest": "123"}, {"digest": "456"}]
        mock_query.return_value = {"transport_success": True, "raw_output": "out", "latency_ms": 100}
        mock_open_file.return_value.__enter__.return_value.read.return_value = self.fixtures_json
        
        runner = DummyRunner()
        agg_result, _ = runner.run_experiment("dummy", "dummy", ["condA", "condB"])
        
        self.assertEqual(agg_result["model_identity_verification"], "CHANGED")
        self.assertEqual(agg_result["run_validity"], "FLAGGED")

    @patch('runner_v3.get_model_metadata')
    @patch('runner_v3.query_ollama')
    @patch('builtins.open')
    @patch('os.makedirs')
    @patch('os.path.exists', return_value=True)
    def test_identity_stable(self, mock_exists, mock_makedirs, mock_open_file, mock_query, mock_metadata):
        mock_metadata.return_value = {"digest": "123"}
        mock_query.return_value = {"transport_success": True, "raw_output": "out", "latency_ms": 100}
        mock_open_file.return_value.__enter__.return_value.read.return_value = self.fixtures_json
        
        runner = DummyRunner()
        agg_result, _ = runner.run_experiment("dummy", "dummy", ["condA", "condB"])
        
        self.assertEqual(agg_result["model_identity_verification"], "VERIFIED_STABLE")
        self.assertEqual(agg_result["run_validity"], "VALID")

if __name__ == '__main__':
    unittest.main()
