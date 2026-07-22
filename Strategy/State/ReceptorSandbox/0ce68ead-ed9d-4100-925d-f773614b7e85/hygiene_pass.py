import sys
with open(r'D:\infinite\Infinity\Strategy\strategy_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_load = '''        with open(self.state_file, "r") as f:
            data = json.load(f).get("mission_shadow_v2", {})
            
        with open(self.state_file, "r") as f:
            raw_data = json.load(f)
        
        data = raw_data.get("mission_shadow_v2", raw_data)'''
new_load = '''        with open(self.state_file, "r") as f:
            raw_data = json.load(f)
        data = raw_data.get("mission_shadow_v2", raw_data)'''
text = text.replace(old_load, new_load)

old_emit = '''        if ledger is None:
            with open(self.state_file, "r") as f:
                state = json.load(f)
            working_ledger = state.get("mission_shadow_v2", {})
            working_ledger = self._load_shadow_ledger()'''
new_emit = '''        if ledger is None:
            working_ledger = self._load_shadow_ledger()'''
text = text.replace(old_emit, new_emit)

with open(r'D:\infinite\Infinity\Strategy\strategy_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)

with open(r'D:\infinite\Infinity\Strategy\ecosystem_mapping_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_volatile = '''    VOLATILE_FIELDS = [
        "verified_claims_count",
        "last_verified_cycle",
        "broken_receipts_log_hash",
        "broken_witness_log_hash",
        "status", "verified_claims_count"
    ]'''
new_volatile = '''    VOLATILE_FIELDS = [
        "verified_claims_count",
        "last_verified_cycle",
        "broken_receipts_log_hash",
        "broken_witness_log_hash",
        "status"
    ]'''
text = text.replace(old_volatile, new_volatile)

with open(r'D:\infinite\Infinity\Strategy\ecosystem_mapping_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Hygiene pass applied!')

# Simple comment
