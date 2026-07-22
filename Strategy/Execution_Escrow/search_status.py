import sys

with open(r"D:\Infinite\Infinity\Strategy\Execution_Escrow\F8_1_Market_Dynamics_Engine.py", "r") as f:
    lines = f.readlines()

matches = []
for i, line in enumerate(lines):
    if "m['status'] =" in line or 'm["status"] =' in line:
        matches.append(f"Line {i+1}: {line.strip()}")

print(f"MATCHES: {len(matches)}")
for m in matches:
    print(m)
