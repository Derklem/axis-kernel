import os, json, glob, hashlib
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
STRATEGY = os.path.join(ROOT, "Strategy")
STATE = os.path.join(STRATEGY, "State")
RECEIPTS = os.path.join(STATE, "Receipts")
VOICE = os.path.join(ROOT, "Runtime", "Decision", "axis_voice.json")
FROM = os.path.join(ROOT, "Communication", "FROM_AXS")

def load(path, default):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        return default

def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def hobj(obj, domain):
    return hashlib.sha256((f"AXIS::{domain}::" + canon(obj)).encode("utf-8")).hexdigest()

state = load(os.path.join(STATE, "strategy_state.json"), {})
ledger = state.get("mission_shadow_v2", {})
anchor = load(os.path.join(STATE, "calibration_continuity_anchor.json"), {})
candidates = load(os.path.join(STATE, "claim_candidates.json"), {}).get("candidates", {})

problems = []
findings = []

# 1. Ledger / anchor comparison
lh = ledger.get("witness_chain_head")
ah = anchor.get("witness_chain_head")
if lh != ah:
    problems.append("witness_head_mismatch")
findings.append(f"ledger_witness_head={str(lh)[:16]}")
findings.append(f"anchor_witness_head={str(ah)[:16]}")

lc = ledger.get("cycle_count")
ac = anchor.get("last_cycle")
findings.append(f"ledger_cycle={lc}")
findings.append(f"anchor_cycle={ac}")
if lc != ac:
    problems.append("cycle_mismatch")

integrity = ledger.get("calibration_ledger_integrity", {}).get("status", "unknown")
continuity = ledger.get("calibration_ledger_integrity", {}).get("continuity_status", "unknown")
findings.append(f"integrity={integrity}")
findings.append(f"continuity={continuity}")
if integrity != "valid":
    problems.append(f"integrity_status_{integrity}")
if continuity not in ("intact", "unknown", None):
    problems.append(f"continuity_status_{continuity}")

# 2. Receipt chain analysis
receipt_files = glob.glob(os.path.join(RECEIPTS, "*.receipt"))
receipts = []
for f in receipt_files:
    r = load(f, None)
    if r:
        r["_file"] = os.path.basename(f)
        receipts.append(r)

parents = {}
dupe_parents = []
for r in receipts:
    p = r.get("parent_receipt_head")
    if p in parents:
        dupe_parents.append((p, parents[p].get("_file"), r.get("_file")))
    else:
        parents[p] = r

if dupe_parents:
    problems.append("duplicate_receipt_parent_heads")

# Walk canonical chain
head = "none"
chain = []
seen = set()
while head in parents and head not in seen:
    seen.add(head)
    r = parents[head]
    chain.append(r)
    head = hobj({"parent_head": r.get("parent_receipt_head"), "causal_hash": r.get("causal_hash")}, "ecosystem_receipt_chain")

orphans = [r for r in receipts if r not in chain]

findings.append(f"receipt_files={len(receipts)}")
findings.append(f"canonical_chain_length={len(chain)}")
findings.append(f"orphan_receipts={len(orphans)}")
findings.append(f"duplicate_parent_count={len(dupe_parents)}")
findings.append(f"computed_receipt_head={head[:16]}")
findings.append(f"ledger_receipt_head={str(ledger.get('ecosystem_receipts_head'))[:16]}")

if head != ledger.get("ecosystem_receipts_head"):
    problems.append("ecosystem_receipt_head_mismatch")
if orphans:
    problems.append("orphan_receipts_detected")

# 3. Candidate state
findings.append(f"candidate_count={len(candidates)}")
for cid, c in list(candidates.items())[:10]:
    findings.append(f"candidate:{cid[:8]} entity={c.get('entity')} domain={c.get('claim_domain')} survived={c.get('cycles_survived')} source={c.get('source_type')}")

# 4. Recommendation
if "duplicate_receipt_parent_heads" in problems or "orphan_receipts_detected" in problems:
    recommendation = "Do not run new cycles. The likely fault is receipt-chain branching/orphaning. Next step: archive current receipts, identify branch point, then choose either surgical chain repair or clean forensic reanchor."
elif "witness_head_mismatch" in problems or "cycle_mismatch" in problems:
    recommendation = "Do not run new cycles. The likely fault is anchor/ledger witness mismatch. Next step: compare forensic_witness_ledger tail against anchor and ledger heads."
elif integrity != "valid":
    recommendation = "Do not run new cycles. Integrity latch is active. Next step: inspect calibration hash inputs before any repair."
else:
    recommendation = "Continuity appears structurally recoverable. Next step: run one read-only derivability audit before considering reanchor."

voice = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "speaker": "AXIS",
    "message_type": "forensic_triage",
    "priority": "high" if problems else "normal",
    "epoch": lc,
    "last_updated_cycle": lc,
    "message": recommendation,
    "evidence": findings,
    "problems": problems,
    "requires_response": True
}

os.makedirs(os.path.dirname(VOICE), exist_ok=True)
tmp = VOICE + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(voice, f, indent=2, ensure_ascii=False)
os.replace(tmp, VOICE)

os.makedirs(FROM, exist_ok=True)
report = os.path.join(FROM, "forensic_triage_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + ".json")
with open(report, "w", encoding="utf-8") as f:
    json.dump(voice, f, indent=2, ensure_ascii=False)

print(json.dumps(voice, indent=2, ensure_ascii=False))
print("\nREPORT:", report)

if dupe_parents:
    print("\nDUPLICATE PARENTS:")
    for p, a, b in dupe_parents[:20]:
        print(p[:16], a, b)

if orphans:
    print("\nORPHANS:")
    for r in orphans[:20]:
        print(r.get("_file"), r.get("mutation_type"), str(r.get("parent_receipt_head"))[:16])
