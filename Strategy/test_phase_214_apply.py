import os
import sys
import json
import uuid
import hashlib
import subprocess
from datetime import datetime
import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE = os.path.join(BASE_DIR, "receptor_pipeline.py")
CONSOLE = os.path.join(BASE_DIR, "receptor_console.py")
REPLAY = os.path.join(BASE_DIR, "replay_receptor_chain.py")

def run_test():
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["AXIS_STATE_DIR"] = temp_dir
        os.environ["AXIS_LEDGER_PATH"] = os.path.join(temp_dir, "receptor_ledger.jsonl")

        TEST_LEDGER = os.environ["AXIS_LEDGER_PATH"]

        def write_receipt(receipt):
            with open(TEST_LEDGER, "a", encoding="utf-8") as f:
                f.write(json.dumps(receipt) + "\n")

        # 1. Initialize Genesis
        payload_str = json.dumps({"message": "Genesis"}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        phash = hashlib.sha256(payload_str).hexdigest()
        ts = datetime.utcnow().isoformat() + "Z"
        rhash = hashlib.sha256(f"GENESIS|GENESIS|GENESIS|{phash}|{ts}".encode("utf-8")).hexdigest()
        write_receipt({
            "event_type": "GENESIS",
            "case_id": "GENESIS",
            "parent_receptor_head": "GENESIS",
            "payload": {"message": "Genesis"},
            "payload_hash": phash,
            "receipt_hash": rhash,
            "timestamp": ts
        })
        parent = rhash

        # Create a dummy target file
        target_file = os.path.join(temp_dir, "dummy_target.py")
        with open(target_file, "w") as f:
            f.write("def test():\n    pass\n")

        # We need a relative path from the perspective of git!
        # Actually, our script just runs git apply --check. Git needs to know the path.
        # It's better to just use a real file in our Strategy directory for the test, but restore it after.
        # Let's use a temporary dummy file in the repo root or Strategy dir.
        real_dummy_path = os.path.join(BASE_DIR, "dummy_phase214.py")
        with open(real_dummy_path, "w") as f:
            f.write("# old\n")

        try:
            subprocess.run(["git", "add", "dummy_phase214.py"], cwd=BASE_DIR, check=True)

            target_case_id = str(uuid.uuid4())

            # OBSERVATION
            payload = {"target_file": "Strategy/dummy_phase214.py", "diff_content": "+# new"}
            phash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
            rhash = hashlib.sha256(f"RECEPTOR_OBSERVATION_RECORDED|{target_case_id}|{parent}|{phash}|{ts}".encode("utf-8")).hexdigest()
            write_receipt({
                "event_type": "RECEPTOR_OBSERVATION_RECORDED",
                "case_id": target_case_id,
                "parent_receptor_head": parent,
                "payload": payload,
                "payload_hash": phash,
                "receipt_hash": rhash,
                "timestamp": ts
            })
            parent = rhash

            # QUARANTINE
            payload = {"reason": "semantic_validator_surface_risk"}
            phash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
            rhash = hashlib.sha256(f"RECEPTOR_DELTA_QUARANTINED|{target_case_id}|{parent}|{phash}|{ts}".encode("utf-8")).hexdigest()
            write_receipt({
                "event_type": "RECEPTOR_DELTA_QUARANTINED",
                "case_id": target_case_id,
                "parent_receptor_head": parent,
                "payload": payload,
                "payload_hash": phash,
                "receipt_hash": rhash,
                "timestamp": ts
            })
            parent = rhash

            with open(os.path.join(temp_dir, "receptor_chain_head.json"), "w") as f:
                json.dump({"head": parent}, f)

            # 3. Create a patch
            patch_path = os.path.join(temp_dir, "test_recovery.patch")
            with open(patch_path, "w", newline='\n') as f:
                f.write("diff --git a/Strategy/dummy_phase214.py b/Strategy/dummy_phase214.py\n")
                f.write("--- a/Strategy/dummy_phase214.py\n")
                f.write("+++ b/Strategy/dummy_phase214.py\n")
                f.write("@@ -1,1 +1,2 @@\n")
                f.write(" # old\n")
                f.write("+# new\n")

            # 4. Propose recovery (should mock ACCEPT)
            os.environ["DUMMY_VERDICT"] = "ACCEPT"
            print("Proposing recovery...")
            subprocess.run([sys.executable, PIPELINE, "--propose-recovery", target_case_id, patch_path, "--audit-with", "dummy_adapter"], check=True)

            # dump ledger
            print("\n--- LEDGER CONTENTS ---")
            with open(TEST_LEDGER, "r") as f:
                print(f.read())
            print("-----------------------\n")

            # 5. Apply recovery
            print("\nApplying recovery...")
            subprocess.run([sys.executable, PIPELINE, "--apply-recovery", target_case_id, "--force-apply"], check=True)

            # 6. Check console output
            print("\n--- Running console --debt-map ---")
            subprocess.run([sys.executable, CONSOLE, "--debt-map"], check=True)

            # 7. Check replay invariants
            print("\n--- Running replay validation ---")
            subprocess.run([sys.executable, REPLAY], check=True)

            print("\nPhase 214 test completed successfully.")
        finally:
            # Clean up dummy file
            if os.path.exists(real_dummy_path):
                os.remove(real_dummy_path)
        # Remove from git index if added
        subprocess.run(["git", "rm", "--cached", "dummy_phase214.py"], cwd=BASE_DIR, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    run_test()
