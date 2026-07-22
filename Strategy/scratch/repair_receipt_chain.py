"""Phase 191 Stage 4.3R: Receipt Chain Repair — Quarantine Orphan Receipts.

Identifies the orphan branches at the two chain collision points and
moves them to a quarantine directory. Does not delete any receipts.
"""
import sys, json, os, glob, copy, shutil
sys.path.append(r"D:\infinite\Infinity\Strategy")
from axis_crypto_helpers import _hash_obj

receipt_dir = r"D:\Infinite\Infinity\Strategy\State\Receipts"
quarantine_dir = os.path.join(receipt_dir, "Quarantined_Orphans")
os.makedirs(quarantine_dir, exist_ok=True)

# Load all receipts
files = glob.glob(os.path.join(receipt_dir, "*.receipt"))
by_parent = {}
receipt_map = {}  # causal_hash -> (filepath, receipt)
for f in files:
    with open(f, "r") as fh:
        r = json.load(fh)
    parent = r.get("parent_receipt_head", "MISSING")
    by_parent.setdefault(parent, []).append((f, r))
    receipt_map[r.get("causal_hash")] = (f, r)

print("Total receipts: {}".format(len(files)))

def compute_next_head(parent_head, receipt):
    r_copy = copy.deepcopy(receipt)
    r_copy.pop("receipt_id", None)
    ch = r_copy.pop("causal_hash", None)
    link = {"parent_head": parent_head, "causal_hash": ch}
    return _hash_obj(link, "ecosystem_receipt_chain")

def trace_branch(parent_head, receipt, by_parent, max_depth=1000):
    """Trace a branch and return all file paths in it."""
    paths = []
    head = compute_next_head(parent_head, receipt)
    depth = 1
    while head in by_parent:
        entries = by_parent[head]
        if len(entries) > 1:
            break  # Stop at next fork
        f2, r2 = entries[0]
        paths.append(f2)
        r2c = copy.deepcopy(r2)
        r2c.pop("receipt_id", None)
        ch2 = r2c.pop("causal_hash", None)
        link2 = {"parent_head": head, "causal_hash": ch2}
        head = _hash_obj(link2, "ecosystem_receipt_chain")
        depth += 1
        if depth > max_depth:
            break
    return paths, head

# Walk the canonical chain to find collision points
print("Walking canonical chain from genesis...")
current = "none"
chain_count = 0
orphan_files = []

while current in by_parent:
    entries = by_parent[current]
    if len(entries) > 1:
        # COLLISION — determine canonical vs orphan
        # Trace both forks, the one that leads further OR to expected head is canonical
        fork_results = []
        for i, (f, r) in enumerate(entries):
            branch_files, final_head = trace_branch(current, r, by_parent)
            fork_results.append((i, f, r, branch_files, final_head, len(branch_files)))
        
        # Sort by depth — longest fork is canonical
        fork_results.sort(key=lambda x: x[5], reverse=True)
        canonical = fork_results[0]
        orphans = fork_results[1:]
        
        print()
        print("COLLISION at position {} (parent: {}...)".format(chain_count, current[:16]))
        print("  CANONICAL: {} ({} children)".format(
            canonical[2].get("mutation_type"), canonical[5]))
        
        for orphan in orphans:
            orphan_file = orphan[1]  # The fork root file
            orphan_children = orphan[3]
            all_orphan = [orphan_file] + orphan_children
            print("  ORPHAN: {} ({} total files to quarantine)".format(
                orphan[2].get("mutation_type"), len(all_orphan)))
            orphan_files.extend(all_orphan)
        
        # Continue with canonical fork
        f, r = canonical[1], canonical[2]
    else:
        f, r = entries[0]
    
    # Advance
    current = compute_next_head(current, r)
    chain_count += 1

print()
print("Canonical chain walked: {} receipts".format(chain_count))
print("Orphan files identified: {}".format(len(orphan_files)))

# Quarantine orphan files
if orphan_files:
    print()
    print("Quarantining {} orphan receipts...".format(len(orphan_files)))
    moved = 0
    for fp in orphan_files:
        if os.path.exists(fp):
            dest = os.path.join(quarantine_dir, os.path.basename(fp))
            shutil.move(fp, dest)
            moved += 1
    print("Moved {} files to {}".format(moved, quarantine_dir))
else:
    print("No orphans to quarantine.")

# Verify chain is now clean
print()
print("=== POST-QUARANTINE VERIFICATION ===")
files_after = glob.glob(os.path.join(receipt_dir, "*.receipt"))
by_parent_after = {}
for f in files_after:
    with open(f, "r") as fh:
        r = json.load(fh)
    parent = r.get("parent_receipt_head", "MISSING")
    by_parent_after.setdefault(parent, []).append((f, r))

dupes_after = {k: v for k, v in by_parent_after.items() if len(v) > 1}
print("Receipts remaining: {}".format(len(files_after)))
print("Duplicate parent heads: {}".format(len(dupes_after)))

# Walk clean chain
current = "none"
clean_count = 0
while current in by_parent_after:
    entries = by_parent_after[current]
    if len(entries) > 1:
        print("ERROR: Still have collision at {}".format(current[:16]))
        break
    f, r = entries[0]
    current = compute_next_head(current, r)
    clean_count += 1

ledger_path = os.path.join(r"D:\Infinite\Infinity\Strategy", "State", "strategy_state.json")
with open(ledger_path, "r") as f:
    state = json.load(f)
expected = state.get("mission_shadow_v2", {}).get("ecosystem_receipts_head", "none")

print("Clean chain length: {}".format(clean_count))
print("Expected head: {}...".format(expected[:24]))
print("Actual head: {}...".format(current[:24]))
print("MATCH: {}".format(current == expected))

if current == expected and len(dupes_after) == 0:
    print()
    print("RECEIPT CHAIN REPAIR: SUCCESS")
    print("Chain is now clean with no collisions.")
else:
    print()
    print("RECEIPT CHAIN REPAIR: NEEDS ATTENTION")
