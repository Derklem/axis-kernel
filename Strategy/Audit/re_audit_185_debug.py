import sys, os, glob, json
from collections import defaultdict
sys.path.append(r'D:\infinite\Infinity\Strategy')
from strategy_engine import StrategyEngine
from ecosystem_mapping_engine import EcosystemMappingEngine

STRATEGY_DIR = r'D:\infinite\Infinity\Strategy'
engine = StrategyEngine()
mapper = EcosystemMappingEngine(root_dir=r'D:\infinite')

ids = {
    'benign': mapper.get_claim_id('factual_benchmark', 'The ecosystem receipt chain maintains exactly one genesis root after Cold Zero supersession.'),
    'ambiguous': mapper.get_claim_id('ambiguous_probe', 'Predictive turbulence will exceed threshold 0.8 within the next 20 cycles due to compounding observation drift.'),
    'weak': mapper.get_claim_id('circular_logic_test', 'The system is functioning perfectly because all perfectly functioning systems report that they are functioning perfectly.')
}

candidates = mapper._load_candidates().get('candidates', {})
anomalies = mapper._load_anomalies().get('anomalies', {})

print('--- Claim Fates ---')
for k, cid in ids.items():
    if cid in candidates:
        loc = 'CANDIDATE_POOL'
        data = candidates[cid]
        print(f'{k.capitalize()} Claim: {loc} (Conf: {data.get("structural_confidence", "N/A")})')
    elif cid in anomalies:
        loc = 'ANOMALY_VAULT'
        data = anomalies[cid]
        print(f'{k.capitalize()} Claim: {loc} (Status: {data.get("status")}, Reason: {data.get("suspension_reason")})')
    else:
        print(f'{k.capitalize()} Claim: FRACTURED/REJECTED')

# Audit Receipts
receipts_dir = os.path.join(STRATEGY_DIR, 'State', 'Receipts')
receipt_files = glob.glob(os.path.join(receipts_dir, '*.receipt'))

by_hash = {}
children_map = defaultdict(list)
genesis_roots = []

for r_path in receipt_files:
    with open(r_path, 'r') as f:
        r = json.load(f)
        r_copy = dict(r)
        r_copy.pop('receipt_id', None)
        causal = r_copy.pop('causal_hash', None)
        parent = r.get('parent_receipt_head', 'none')
        
        chain_hash = mapper._compute_domain_hash('ecosystem_receipt_chain', {'parent_head': parent, 'causal_hash': causal})
        by_hash[chain_hash] = {'parent': parent, 'path': r_path}
        children_map[parent].append(chain_hash)
        if parent == 'none':
            genesis_roots.append(chain_hash)

branch_points = [p for p, c in children_map.items() if len(c) > 1]
print(f'\nChain Integrity - Roots: {len(genesis_roots)}, Branches: {len(branch_points)}')

ledger = engine._load_shadow_ledger()
model = mapper._load_model()
candidates_full = mapper._load_candidates()
anomalies_full = mapper._load_anomalies()
baseline_path = os.path.join(STRATEGY_DIR, 'State', 'ecosystem_model_baseline.json')
expected_baseline_hash = mapper._hash_file_domain(baseline_path, 'ecosystem_baseline')

ok, errors = mapper.verify_state_derivability(
    model=model,
    receipt_dir=engine.receipt_dir,
    baseline_path=baseline_path,
    expected_baseline_hash=expected_baseline_hash,
    current_candidates=candidates_full,
    current_anomalies=anomalies_full,
    expected_head=ledger.get('ecosystem_receipts_head'),
    expected_cycle=ledger.get('cycle_count')
)

print(f'\nDerivability: {"PASSED" if ok else "FAILED"}')
if not ok:
    for e in errors: print(e)
