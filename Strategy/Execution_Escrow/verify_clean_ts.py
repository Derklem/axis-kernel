import sys

with open(r"D:\Infinite\Infinity\Strategy\Execution_Escrow\F8_4_Market_Observability.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

matches = []
for i, line in enumerate(lines):
    if "clean_ts" in line or "fromisoformat(clean_ts)" in line:
        matches.append(f"Line {i+1}: {line.strip()}")

print(f"MATCHES: {len(matches)}")
for m in matches:
    print(m)
