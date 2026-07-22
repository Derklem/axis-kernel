import sys

test_path = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\test_f8_8_calibration.py"

p1 = 'mock_prediction("T4")'
p2 = 'After 4 resolutions'
p3 = 'After 6 resolutions'
p4 = 'After 8 resolutions'

c1 = c2 = c3 = c4 = 0

with open(test_path, "r", encoding="utf-8") as f:
    text = f.read()
    c1 = text.count(p1)
    c2 = text.count(p2)
    c3 = text.count(p3)
    c4 = text.count(p4)

print(f"MATCHES for '{p1}': {c1}")
print(f"MATCHES for '{p2}': {c2}")
print(f"MATCHES for '{p3}': {c3}")
print(f"MATCHES for '{p4}': {c4}")
