import json
import os

cnt_file = 'D:/Infinite/Infinity/Truth_Engine/Content/TE_Content_Nodes.jsonl'
nodes_jan = []
nodes_feb = []
nodes_recent = []

if os.path.exists(cnt_file):
    with open(cnt_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                node = json.loads(line)
                ts = node.get('timestamp', '')
                if '2026-01-26' in ts or '2026-01-27' in ts:
                    if len(nodes_jan) < 3: nodes_jan.append(node)
                elif '2026-02-08' in ts:
                    if len(nodes_feb) < 3: nodes_feb.append(node)
                else:
                    nodes_recent.append(node)
            except:
                pass

nodes_recent = nodes_recent[-3:] if len(nodes_recent) >= 3 else nodes_recent

print('--- JAN STRATUM ---')
for n in nodes_jan: print(f"{n.get('id')} | {n.get('timestamp')}")
print('\n--- FEB STRATUM ---')
for n in nodes_feb: print(f"{n.get('id')} | {n.get('timestamp')}")
print('\n--- RECENT STRATUM ---')
for n in nodes_recent: print(f"{n.get('id')} | {n.get('timestamp')}")
