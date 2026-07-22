import os, glob, json, copy, sys
sys.path.append(r'd:\Infinite\Infinity\Strategy')
from axis_crypto_helpers import _hash_obj

receipts_dir = r'd:\Infinite\Infinity\Strategy\State\Receipts'
files = glob.glob(os.path.join(receipts_dir, '*.receipt'))
errors = []

for r_path in files:
    with open(r_path, 'r') as f:
        r = json.load(f)
        
    r_copy = copy.deepcopy(r)
    r_id = r_copy.pop('receipt_id', None)
    r_hash = r_copy.pop('causal_hash', None)
    actual_r_hash = _hash_obj(r_copy, domain='ecosystem_receipt')
    
    if actual_r_hash != r_hash:
        errors.append(f'{r_id} : {actual_r_hash} != {r_hash}')

print('Errors:', errors)
