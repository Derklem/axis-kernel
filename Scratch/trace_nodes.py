import os
import json

targets = {
    'CNT-453f62c18dfcee83': 'Jan 26',
    'CNT-20260131-dffbb972': 'Jan 31',
    'CNT-20260606-7091055c': 'June 7'
}

results = {k: [] for k in targets}

for root, dirs, files in os.walk('D:/Infinite'):
    for file in files:
        if file.endswith(('.json', '.jsonl', '.ps1', '.md', '.txt', '.log', '.bak', '.old')):
            path = os.path.join(root, file)
            # skip the content nodes ledger itself
            if 'TE_Content_Nodes.jsonl' in path: continue
            
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f):
                        for t in targets:
                            if t in line:
                                results[t].append((path, i+1, line.strip()[:200]))
            except:
                pass

print('--- Node Fate Analysis ---')
for t, name in targets.items():
    print(f'\\nTarget: {t} ({name})')
    if not results[t]:
        print('  Status: DEAD (No downstream references)')
    else:
        print(f'  Status: RECURRENT/TOUCHED ({len(results[t])} references)')
        for r in results[t][:5]:
            print(f'    File: {r[0]}')
            print(f'    Line {r[1]}: {r[2]}')
