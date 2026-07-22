import glob, json
for f in glob.glob(r'D:\infinite\Infinity\Strategy\State\Receipts\*.receipt'):
    with open(f, 'r') as file:
        r = json.load(file)
        if r.get('mutation_type') == 'CANDIDATE_FRACTURED':
            data = r.get('data', {})
            reason = data.get('fracture_reason', data.get('reason'))
            print(f"Fractured: {r.get('target_id')[:8]} Reason: {reason}")
