import os, glob, json, copy, sys
sys.path.append(r'd:\Infinite\Infinity\Strategy')
from axis_crypto_helpers import _hash_obj

receipts_dir = r'd:\Infinite\Infinity\Strategy\State\Receipts'
files = glob.glob(os.path.join(receipts_dir, '*.receipt'))
r_dict = {}

for f in files:
    r = json.load(open(f))
    r_dict[r.get('parent_receipt_head')] = r

head = 'none'
c = 0
while head in r_dict:
    print('Head found:', head)
    r = r_dict[head]
    actual_chain_hash = _hash_obj({'parent_head': head, 'causal_hash': r.get('causal_hash')}, domain='ecosystem_receipt_chain')
    head = actual_chain_hash
    c += 1

print('Total length:', c)
