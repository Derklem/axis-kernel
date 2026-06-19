import unittest
import tempfile
import os
import shutil
import subprocess
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Global state for the mock server
mock_response = {"text": "{}"}

class MockOllamaHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"response": mock_response.get("text", "")}).encode('utf-8'))
        
    def log_message(self, format, *args):
        pass

server = HTTPServer(('127.0.0.1', 0), MockOllamaHandler)
mock_port = server.server_address[1]

def run_server():
    server.serve_forever()

t = threading.Thread(target=run_server, daemon=True)
t.start()

class TestAuditorDrift(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.state_dir = os.path.join(self.test_dir, "State")
        shutil.copytree(os.path.join(BASE_DIR, "State"), self.state_dir)
        
        self.registry_path = os.path.join(self.test_dir, "auditor_registry.json")
        with open(os.path.join(BASE_DIR, "auditors", "auditor_registry.json"), "r") as f:
            reg = json.load(f)
        
        # Point to our mock server
        reg["auditors"]["gemma"]["api_url"] = f"http://127.0.0.1:{mock_port}/api/generate"
        with open(self.registry_path, "w") as f:
            json.dump(reg, f)

        self.env = os.environ.copy()
        self.env["AXIS_STATE_DIR"] = self.state_dir
        self.env["AXIS_REGISTRY_PATH"] = self.registry_path

        self.dummy_diff = os.path.join(self.test_dir, "dummy.diff")
        with open(self.dummy_diff, "w", encoding="utf-8") as f:
            f.write("diff --git a/dummy.py b/dummy.py\n--- a/dummy.py\n+++ b/dummy.py\n@@ -1,1 +1,2 @@\n-old\n+new\n")
            
        with open(os.path.join(self.test_dir, "dummy.py"), "w", encoding="utf-8") as f:
            f.write("new\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _run_pipeline(self, *args):
        cmd = [sys.executable, os.path.join(BASE_DIR, "receptor_pipeline.py")] + list(args)
        return subprocess.run(cmd, env=self.env, capture_output=True, text=True)

    def _verify_replay(self):
        cmd = [sys.executable, os.path.join(BASE_DIR, "replay_receptor_chain.py")]
        res = subprocess.run(cmd, env=self.env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Replay failed:\n{res.stdout}\n{res.stderr}")

    def _get_ledger_receipts(self, event_type):
        receipts = []
        with open(os.path.join(self.state_dir, "receptor_ledger.jsonl"), "r") as f:
            for line in f:
                if not line.strip(): continue
                r = json.loads(line)
                if r["event_type"] == event_type:
                    receipts.append(r)
        return receipts

    def test_1_malformed_json_drift(self):
        # Completely broken text
        mock_response["text"] = "I am an AI and I think this code is good. VERDICT: ACCEPT."
        self._run_pipeline("--check-diff", self.dummy_diff, "--audit")
        
        invalid_receipts = self._get_ledger_receipts("AUDITOR_VERDICT_INVALID")
        self.assertTrue(len(invalid_receipts) > 0)
        self.assertEqual(invalid_receipts[-1]["payload"]["parsing_reliability"], "failed")
        self._verify_replay()

    def test_2_schema_violation(self):
        # Valid JSON but missing required fields
        mock_response["text"] = '{"verdict": "ACCEPT", "reasoning": "Looks good"}'
        self._run_pipeline("--check-diff", self.dummy_diff, "--audit")
        
        invalid_receipts = self._get_ledger_receipts("AUDITOR_VERDICT_INVALID")
        self.assertTrue(len(invalid_receipts) > 0)
        self.assertIn("Missing required field", invalid_receipts[-1]["payload"]["error"])
        self._verify_replay()

    def test_3_overconfident_accept_override(self):
        # Force a physical failure by passing an invalid diff target (target doesn't exist so diff reverse fails)
        bad_diff = os.path.join(self.test_dir, "bad.diff")
        with open(bad_diff, "w", encoding="utf-8") as f:
            f.write("diff --git a/nonexistent.py b/nonexistent.py\n--- a/nonexistent.py\n+++ b/nonexistent.py\n@@ -1,1 +1,2 @@\n-old\n+def 123bad_syntax()\n")
            
        mock_response["text"] = '```json\n{"auditor_id": "gemma", "verdict": "ACCEPT", "confidence": 0.99, "reasoning": "Nothing to worry about", "risks": [], "missing_evidence": []}\n```'
        res = self._run_pipeline("--check-diff", bad_diff, "--audit")
        
        # A nonexistent target causes reverse patch failure -> physical failure (hash_mismatch or similar)
        # Even if Auditor returns ACCEPT, the ledger's final RECEPTOR_EVALUATION_SUMMARY MUST be QUARANTINE
        eval_receipts = self._get_ledger_receipts("CHECK_ONLY")
        self.assertTrue(len(eval_receipts) > 0)
        self.assertEqual(eval_receipts[-1]["payload"]["verdict"], "QUARANTINE")
        self._verify_replay()

    def test_4_false_quarantine(self):
        # Perfectly safe file but Auditor returns QUARANTINE
        mock_response["text"] = '```json\n{"auditor_id": "gemma", "verdict": "QUARANTINE", "confidence": 0.8, "reasoning": "I dont like it", "risks": ["arbitrary"], "missing_evidence": []}\n```'
        self._run_pipeline("--check-diff", self.dummy_diff, "--audit")
        
        # Verify the pipeline respected the QUARANTINE
        eval_receipts = self._get_ledger_receipts("CHECK_ONLY")
        self.assertEqual(eval_receipts[-1]["payload"]["verdict"], "QUARANTINE")
        
        # Verify the auditor verdict is QUARANTINE
        verdicts = self._get_ledger_receipts("AUDITOR_VERDICT_RECEIVED")
        self.assertEqual(verdicts[-1]["payload"]["verdict"], "QUARANTINE")
        self._verify_replay()

    def test_5_high_confidence_drift_on_protected_surface(self):
        # Pass an actual relative path to force the pipeline to recognize it as a protected file
        protected_diff = os.path.join(self.test_dir, "Strategy_receptor_pipeline.diff")
        with open(protected_diff, "w", encoding="utf-8") as f:
            f.write("diff --git a/Strategy/receptor_pipeline.py b/Strategy/receptor_pipeline.py\n--- a/Strategy/receptor_pipeline.py\n+++ b/Strategy/receptor_pipeline.py\n@@ -1,1 +1,2 @@\n-old\n+    pass\n")
        
        # Copy the real pipeline as the mock target so the reverse patch logic correctly flags it
        os.makedirs(os.path.join(self.test_dir, "Strategy"), exist_ok=True)
        shutil.copy(os.path.join(BASE_DIR, "receptor_pipeline.py"), os.path.join(self.test_dir, "Strategy", "receptor_pipeline.py"))
            
        mock_response["text"] = '```json\n{"auditor_id": "gemma", "verdict": "ACCEPT", "confidence": 1.0, "reasoning": "I am sure this is safe", "risks": [], "missing_evidence": []}\n```'
        res = self._run_pipeline("--check-diff", protected_diff, "--audit")
        
        eval_receipts = self._get_ledger_receipts("CHECK_ONLY")
        self.assertTrue(len(eval_receipts) > 0, f"No CHECK_ONLY receipt found! Stdout:\n{res.stdout}\nStderr:\n{res.stderr}")
        self.assertEqual(eval_receipts[-1]["payload"]["verdict"], "QUARANTINE")
        
        # And the auditor's ACCEPT was logged as received, but pipeline state remained QUARANTINE
        verdicts = self._get_ledger_receipts("AUDITOR_VERDICT_RECEIVED")
        self.assertEqual(verdicts[-1]["payload"]["verdict"], "ACCEPT", f"Stdout:\n{res.stdout}\nStderr:\n{res.stderr}")
        
        self._verify_replay()

    def test_6_repair_heuristic_limits(self):
        # Extremely malformed text that cannot be repaired
        mock_response["text"] = "```json\n { verdict: ACCEPT \n```" # Invalid JSON
        self._run_pipeline("--check-diff", self.dummy_diff, "--audit")
        
        invalid_receipts = self._get_ledger_receipts("AUDITOR_VERDICT_INVALID")
        self.assertTrue(len(invalid_receipts) > 0)
        self.assertEqual(invalid_receipts[-1]["payload"]["parsing_reliability"], "failed")
        self._verify_replay()

if __name__ == "__main__":
    unittest.main()
