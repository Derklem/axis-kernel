import os
import sys
import json
import subprocess
from pathlib import Path

def main():
    base_dir = Path(__file__).resolve().parent.parent
    inputs_dir = base_dir / "inputs"
    state_dir = base_dir / "state"

    # 1. Setup genesis state near upper bound
    state = {
        "state_schema_version": "1.1.0",
        "confidence": 100,
        "evidence_count": 9007199254740990,
        "applied_observation_ids": []
    }
    state_path = state_dir / "state_bounds_0.json"
    with open(state_path, "w") as f: json.dump(state, f, indent=2)

    feed_path = inputs_dir / "feed.json"
    spec_path = inputs_dir / "transition_spec.json"

    # 4. Apply feed (should hit cap)
    print("Applying feed to hit evidence count cap...")
    trans_1_path = state_dir / "transition_bounds_1.json"
    res = subprocess.run([
        sys.executable, "-m", "state.cli",
        "--prior-state", str(state_path),
        "--feed", str(feed_path),
        "--spec", str(spec_path),
        "--output", str(trans_1_path)
    ], capture_output=True, text=True)

    if res.returncode == 0:
        with open(trans_1_path, "r") as f:
            t = json.load(f)
        if t["next_state"]["evidence_count"] == 9007199254740991:
            print("Success! State engine correctly clamped evidence_count at SAFE_INTEGER_MAX.")
            if "EVIDENCE_COUNT_CLAMPED" in t["reason_codes"]:
                print("Reason code EVIDENCE_COUNT_CLAMPED was emitted.")
            else:
                print("FAIL! Reason code not emitted.")
                sys.exit(1)
        else:
            print(f"FAIL! Unexpected evidence_count: {t['next_state']['evidence_count']}")
            sys.exit(1)
    else:
        print("FAIL! State engine threw a hard error unexpectedly.")
        print(res.stderr.strip())
        sys.exit(1)

if __name__ == "__main__":
    main()
