import os
import sys
import argparse
import shutil
import subprocess
import json
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description="Initialize Axis Governance System")
    parser.add_argument("--force", action="store_true", help="Overwrite existing ledger, hook, and registry files")
    args = parser.parse_args()

    # Determine paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    
    git_dir = os.path.join(repo_root, ".git")
    if not os.path.isdir(git_dir):
        print("[ERROR] No .git directory found. Must be run in a git repository.")
        sys.exit(1)

    target_hook = os.path.join(git_dir, "hooks", "pre-commit")
    source_hook = os.path.join(script_dir, "hooks", "pre-commit")

    state_dir = os.path.join(script_dir, "State")
    ledger_path = os.path.join(state_dir, "receptor_ledger.jsonl")
    
    auditors_dir = os.path.join(script_dir, "auditors")
    registry_path = os.path.join(auditors_dir, "auditor_registry.json")

    print("--- Axis Initialization ---")

    # 1. Install Hook
    if not os.path.exists(source_hook):
        print(f"[ERROR] Source hook template not found at {source_hook}")
        sys.exit(1)

    if os.path.exists(target_hook) and not args.force:
        print(f"[*] Hook already exists at {target_hook}. Skipping (use --force to overwrite).")
    else:
        shutil.copy2(source_hook, target_hook)
        print(f"[+] Installed pre-commit hook to {target_hook}")

    # 2. Setup State & Ledger
    os.makedirs(state_dir, exist_ok=True)
    if os.path.exists(ledger_path) and not args.force:
        print(f"[*] Ledger already exists at {ledger_path}. Skipping (use --force to overwrite).")
    else:
        with open(ledger_path, "w") as f:
            pass # Creating an empty file is sufficient. The pipeline handles initialization.
        print(f"[+] Created empty ledger at {ledger_path}")

    # 3. Setup Auditor Registry
    os.makedirs(auditors_dir, exist_ok=True)
    if os.path.exists(registry_path) and not args.force:
        print(f"[*] Auditor registry already exists at {registry_path}. Skipping (use --force to overwrite).")
    else:
        default_registry = {
            "auditors": [
                {
                    "id": "dummy_auditor",
                    "module": "dummy_adapter",
                    "active": True
                }
            ],
            "default_strategy": "ANY_QUARANTINE_WINS"
        }
        with open(registry_path, "w") as f:
            json.dump(default_registry, f, indent=4)
        print(f"[+] Created default auditor registry at {registry_path}")

    # 4. Verification runs
    print("\n--- Running Verification ---")
    
    replay_script = os.path.join(script_dir, "replay_receptor_chain.py")
    if os.path.exists(replay_script):
        subprocess.run([sys.executable, replay_script], cwd=repo_root)
    else:
        print("[!] replay_receptor_chain.py not found, skipping replay check.")

    console_script = os.path.join(script_dir, "receptor_console.py")
    if os.path.exists(console_script):
        subprocess.run([sys.executable, console_script, "--status"], cwd=repo_root)
    else:
        print("[!] receptor_console.py not found, skipping status check.")

    print("\n[+] Axis Governance System initialization complete.")

if __name__ == "__main__":
    main()
