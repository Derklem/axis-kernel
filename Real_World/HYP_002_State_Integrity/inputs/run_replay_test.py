import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

def main():
    base_dir = Path(__file__).resolve().parent.parent
    inputs_dir = base_dir / "inputs"
    state_dir = base_dir / "state"

    for d in [state_dir]:
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    # 1. Setup genesis state
    state = {
        "state_schema_version": "1.1.0",
        "confidence": 0,
        "evidence_count": 0,
        "applied_observation_ids": []
    }
    state_path = state_dir / "state_0.json"
    with open(state_path, "w") as f: json.dump(state, f, indent=2)

    # 2. Setup mock observation
    obs_id = "OBS_1234567890abcdef1234567890abcdef"
    feed = {
        "observation_schema_version": "1.0.0",
        "kind": "feed",
        "observations": [
            {
                "observation_id": obs_id,
                "subject": "hyp-002",
                "support": 1,
                "reason_code": "MATCH",
                "source": {
                    "run_id": "RUN_123",
                    "receipt_hash": "a"*64,
                    "verification_root": "b"*64,
                    "artifact_path": "evaluation.json",
                    "artifact_hash": "c"*64
                }
            }
        ]
    }
    feed_path = inputs_dir / "feed.json"
    with open(feed_path, "w") as f: json.dump(feed, f, indent=2)

    # 3. Setup mock transition spec
    transition_spec = {
        "transition_spec_schema_version": "1.0.0",
        "transition_version": "state-hyp002",
        "subject": "hyp-002",
        "supported_increment": 5
    }
    spec_path = inputs_dir / "transition_spec.json"
    with open(spec_path, "w") as f: json.dump(transition_spec, f, indent=2)

    # 4. First application (should succeed)
    print("Applying feed for the first time...")
    trans_1_path = state_dir / "transition_1.json"
    subprocess.run([
        sys.executable, "-m", "state.cli",
        "--prior-state", str(state_path),
        "--feed", str(feed_path),
        "--spec", str(spec_path),
        "--output", str(trans_1_path)
    ], check=True)
    
    with open(trans_1_path, "r") as f:
        t1 = json.load(f)
    out_1_path = state_dir / "state_1.json"
    with open(out_1_path, "w") as f:
        json.dump(t1["next_state"], f, indent=2)

    print("Success! state_1.json produced.")

    # 5. Second application (should fail)
    print("Applying identical feed for the second time (REPLAY)...")
    trans_2_path = state_dir / "transition_2.json"
    res = subprocess.run([
        sys.executable, "-m", "state.cli",
        "--prior-state", str(out_1_path),
        "--feed", str(feed_path),
        "--spec", str(spec_path),
        "--output", str(trans_2_path)
    ], capture_output=True, text=True)

    if res.returncode == 0:
        with open(trans_2_path, "r") as f:
            t2 = json.load(f)
        if "OBS_1234567890abcdef1234567890abcdef" in t2["skipped_observation_ids"]:
            print("Success! State engine gracefully skipped the replay.")
            if t2["prior_state_root"] == t2["next_state_root"]:
                print("State vector was NOT mutated.")
            else:
                print("FAIL! State vector mutated during a skip.")
                sys.exit(1)
        else:
            print("FAIL! State engine did not skip the replayed observation.")
            sys.exit(1)
    else:
        print("FAIL! State engine threw a hard error.")
        sys.exit(1)

if __name__ == "__main__":
    main()
