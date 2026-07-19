import json
import hashlib
d = {
    "z": [],
    "a": {},
    "b": "\\\"\b\f\n\r\t",
    "c": "こんにちは",
    "d": [3, 2, 1]
}
s = json.dumps(d, separators=(',', ':'), sort_keys=True)
print("PYTHON JSON:", s)
