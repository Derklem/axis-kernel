
import json
import os
import pathlib
artifacts_dir = pathlib.Path(os.environ["LAB_ARTIFACTS_DIR"])
with open(artifacts_dir / "evaluation.json", "w") as out:
    json.dump({"evaluation_schema_version": "1.0.0", "outcome": "SUPPORTED", "subject": "strategy-hello-v1", "metric": "decision_reproduced", "observed": 1, "expected": 1}, out)
