import os, sys, json
sys.path.append(r'd:\Infinite\Infinity\Strategy')
from ecosystem_mapping_engine import EcosystemMappingEngine
from strategy_engine import StrategyEngine

engine = StrategyEngine()
model = engine.ecosystem_mapper._load_model()
receipt_dir = r'd:\Infinite\Infinity\Strategy\State\Receipts'
baseline_path = r'd:\Infinite\Infinity\Strategy\State\ecosystem_model_baseline.json'
l = engine._load_shadow_ledger()
expected_baseline_hash = l.get('baseline_model_hash')

candidates = engine.ecosystem_mapper._load_candidates()

print("Running derivability...")
ok, errors = engine.ecosystem_mapper.verify_state_derivability(model, receipt_dir, baseline_path, expected_baseline_hash, current_candidates=candidates)
print(f"OK: {ok}, Errors: {errors}")
