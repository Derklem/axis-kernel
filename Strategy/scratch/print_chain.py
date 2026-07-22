import json, glob, sys
sys.path.append(r'd:\Infinite\Infinity\Strategy')
from axis_crypto_helpers import _hash_obj

files = glob.glob(r'd:\Infinite\Infinity\Strategy\State\Receipts\*.receipt')
d = {json.load(open(f)).get('parent_receipt_head'): json.load(open(f)) for f in files}
h = 'none'

while h in d:
    r = d[h]
    print(r.get('mutation_type'), r.get('receipt_id'))
    h = _hash_obj({'parent_head': h, 'causal_hash': r.get('causal_hash')}, domain='ecosystem_receipt_chain')
