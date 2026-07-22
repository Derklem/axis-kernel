import sys

with open(r"D:\Infinite\Infinity\Strategy\Execution_Escrow\F8_4_Market_Observability.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("--- Source Check ---")
for i, line in enumerate(lines):
    if "def parse_ts" in line or "t.get('epistemic_status', 'ACTIVE') != 'RETIRED'" in line or "parsed = parse_ts(ts)" in line:
        print(f"L{i+1}: {line.strip()}")
