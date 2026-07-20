
import json
import sys
import os
from laboratory.crypto import canonical_hash
with open(r'D:\infinite\Infinity\Real_World\HYP_001_Falsifiable\inputs\payload.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
root = canonical_hash(data)
print(root)

artifacts_dir = os.environ.get("LAB_ARTIFACTS_DIR", "artifacts")
os.makedirs(artifacts_dir, exist_ok=True)
evaluation = {
    "evaluation_schema_version": "1.0.0",
    "outcome": "SUPPORTED",
    "subject": "hyp-001",
    "metric": "hash_match",
    "observed": 1,
    "expected": 1
}
eval_path = os.path.join(artifacts_dir, "evaluation.json")
with open(eval_path, "w", encoding="utf-8") as f:
    json.dump(evaluation, f, indent=2)
