import sys, json, os, glob, copy
sys.path.append(r'D:\infinite\Infinity\Strategy')
from strategy_engine import StrategyEngine
engine = StrategyEngine()
mapper = engine.ecosystem_mapper

baseline_path = os.path.join(mapper.state_dir, 'ecosystem_model_baseline.json')
with open(baseline_path, 'r') as f: test_model = json.load(f)

test_candidates = {"candidates": test_model.get('claim_candidates', {})}
test_anomalies = {"anomalies": test_model.get('speculative_anomalies', {})}

receipts = glob.glob(os.path.join(engine.receipt_dir, '*.receipt'))
chain = {}
roots = []
for r in receipts:
    with open(r, 'r') as f:
        data = json.load(f)
        parent = data.get('parent_receipt_head')
        if parent == 'none': roots.append(r)
        else: chain[parent] = r

ordered = []
curr = roots[0] if roots else None
while curr:
    ordered.append(curr)
    h = curr.split('_')[-1].replace('.receipt', '')
    curr = chain.get(h)

test_cycle = 0
for r in ordered:
    with open(r, 'r') as f: data = json.load(f)
    mapper.apply_receipt_to_model(test_model, data, test_candidates, test_anomalies)
    test_cycle = data.get('cycle_count', test_cycle)

with open(engine.state_file, 'r') as f: live_state = json.load(f)
live_state['mission_shadow_v2']['claim_candidates'] = test_candidates['candidates']
live_state['mission_shadow_v2']['speculative_anomalies'] = test_anomalies['anomalies']
live_state['mission_shadow_v2']['ecosystem_receipts_head'] = ordered[-1].split('_')[-1].replace('.receipt', '') if ordered else 'none'
live_state['mission_shadow_v2']['cycle_count'] = test_cycle
with open(engine.state_file, 'w') as f: json.dump(live_state, f, indent=4)

import subprocess
subprocess.run(['python', r'D:\infinite\Infinity\Strategy\fix_state.py'])
print('Restored perfectly from receipts!')
