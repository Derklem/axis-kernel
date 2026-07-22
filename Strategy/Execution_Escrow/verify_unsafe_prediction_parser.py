import sys

fpath = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\F8_4_Market_Observability.py"
patterns = [
    "open_predictions_by_theory[p['theory_id']]",
    "open_predictions_by_theory[p[\"theory_id\"]]"
]

matches = 0
with open(fpath, "r", encoding="utf-8") as f:
    for line in f:
        for p in patterns:
            if p in line:
                matches += 1

print(f"MATCHES: {matches}")
