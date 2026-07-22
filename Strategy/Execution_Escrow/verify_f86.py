import sys

files = [
    r"D:\Infinite\Infinity\Strategy\Execution_Escrow\F8_1_Market_Dynamics_Engine.py",
    r"D:\Infinite\Infinity\Strategy\Execution_Escrow\F8_4_Market_Observability.py"
]

patterns = [
    "forecast block is mandatory",
    "evaluation_after_days",
    "PREDICTIONS_PATH",
    "open_predictions_by_theory"
]

print("--- Source Check ---")
for fpath in files:
    with open(fpath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            for p in patterns:
                if p in line:
                    print(f"[{fpath.split(chr(92))[-1]}] L{i+1}: {line.strip()}")
