import sys

engine_path = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\F8_1_Market_Dynamics_Engine.py"
obs_path = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\F8_4_Market_Observability.py"

p1 = "len(predictions) - resolved_count"
p2 = "\"authenticated_spoof_guard\": authenticated_spoof_guard"

c1 = 0
with open(obs_path, "r", encoding="utf-8") as f:
    for line in f:
        if p1 in line:
            c1 += 1

c2 = 0
with open(engine_path, "r", encoding="utf-8") as f:
    for line in f:
        if p2 in line:
            c2 += 1

print(f"MATCHES for '{p1}': {c1}")
print(f"MATCHES for '{p2}': {c2}")
