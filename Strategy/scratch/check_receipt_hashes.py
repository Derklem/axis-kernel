import os, glob, json, sys
sys.path.append(r'd:\Infinite\Infinity\Strategy')
from axis_crypto_helpers import _hash_obj

receipts_dir = r'd:\Infinite\Infinity\Strategy\State\Receipts'
for f in glob.glob(os.path.join(receipts_dir, '*.receipt')):
    with open(f) as file:
        r = json.load(file)
    r_copy = r.copy()
    r_id = r_copy.pop('receipt_id', None)
    r_hash = r_copy.pop('causal_hash', None)
    actual_r_hash = _hash_obj(r_copy, domain='ecosystem_receipt')
    
    if actual_r_hash != r_hash:
        print(f"Mismatch in {os.path.basename(f)}")
        print(f"Stored: {r_hash}")
        print(f"Actual: {actual_r_hash}")
        print(json.dumps(r_copy, indent=2))
        print("-------------")
