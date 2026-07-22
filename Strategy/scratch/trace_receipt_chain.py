import os, json, sys
sys.path.append(r'd:\infinite\Infinity\Strategy')
from axis_crypto_helpers import _hash_obj

RECEIPTS_DIR = r'd:\infinite\Infinity\Strategy\State\Receipts'

def trace_chain():
    receipts_by_parent = {}
    for f in os.listdir(RECEIPTS_DIR):
        if f.endswith(".receipt"):
            with open(os.path.join(RECEIPTS_DIR, f), "r") as rfile:
                r = json.load(rfile)
                receipts_by_parent[r.get("parent_receipt_head")] = r

    current_head = "none"
    chain = []
    while current_head in receipts_by_parent:
        r = receipts_by_parent[current_head]
        causal_hash = r.get("causal_hash")
        link_data = {"parent_head": current_head, "causal_hash": causal_hash}
        new_head = _hash_obj(link_data, "ecosystem_receipt_chain")
        
        chain.append({
            "id": r.get("receipt_id"),
            "type": r.get("mutation_type"),
            "target": r.get("target_id"),
            "parent": current_head,
            "new_head": new_head
        })
        current_head = new_head
        
    print(f"Chain Length: {len(chain)}")
    for i, link in enumerate(chain):
        print(f"[{i}] {link['type']} -> {link['id'][:20]}... (Parent: {link['parent'][:8]}, Head: {link['new_head'][:12]})")

    # Find the missing candidate in the chain
    target_id = "c0786e63a1ea146c75a0e58699a46738bec706629bf4e0a643a915b3df49d431"
    found = [l for l in chain if l['target'] == target_id]
    print(f"\nTarget Search: {len(found)} entries found for {target_id[:12]}")
    for f in found:
        print(f"  {f['type']} at step {chain.index(f)}")

if __name__ == "__main__":
    trace_chain()
