
import json
import sys
from laboratory.crypto import canonical_hash
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    data = json.load(f)
print(canonical_hash(data))
