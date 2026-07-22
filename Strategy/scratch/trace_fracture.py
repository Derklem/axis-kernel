import os, json, copy, glob, sys
sys.path.append(r'd:\Infinite\Infinity\Strategy')
from axis_crypto_helpers import _hash_obj

r_dir = r'd:\Infinite\Infinity\Strategy\State\Receipts'
files = glob.glob(os.path.join(r_dir, '*.receipt'))
d = {json.load(open(f)).get('parent_receipt_head'): json.load(open(f)) for f in files}
c = {'candidates': {}}
h = 'none'

while h in d:
    r = d[h]
    t = r.get('mutation_type')
    tid = r.get('target_id')
    
    if t == 'CANDIDATE_QUARANTINED':
        c['candidates'][tid] = {}
        print(f"Quarantined: {tid}")
    elif t == 'CANDIDATE_FRACTURED':
        print(f"Fractured: {tid} in candidates? {tid in c['candidates']}")
        
    h = _hash_obj({'parent_head': h, 'causal_hash': r.get('causal_hash')}, domain='ecosystem_receipt_chain')
