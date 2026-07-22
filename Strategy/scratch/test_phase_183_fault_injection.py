import os, sys, json, copy, shutil, glob
from datetime import datetime, timezone

# Add Strategy to path
STRATEGY_DIR = os.path.abspath(r'd:\Infinite\Infinity\Strategy')
if STRATEGY_DIR not in sys.path:
    sys.path.append(STRATEGY_DIR)

from strategy_engine import StrategyEngine
from axis_crypto_helpers import _hash_obj

class MaliciousStrategyEngine(StrategyEngine):
    """A StrategyEngine variant for Phase 183 Fault Injection."""
    
    def inject_orphan_receipt(self, ledger):
        """Injects a receipt with a random parent head (breaking the chain)."""
        print("[!] Injecting ORPHAN_RECEIPT...")
        fake_parent = "deadbeef" * 8
        # We use a real mutation so the state actually changes
        self._emit_ecosystem_mutation_receipt(
            mutation_type="CANDIDATE_QUARANTINED",
            target_id="orphan_target",
            data={"entity": "Ent_Orphan", "claim": "Orphan Claim", "discovery_utc": datetime.now(timezone.utc).isoformat()},
            ledger=ledger
        )
        # Manually corrupt the head in the ledger
        ledger["ecosystem_receipts_head"] = fake_parent
        # Save it to disk so run_once() sees it
        with open(self.state_file, "w") as f:
            json.dump({"mission_shadow_v2": ledger}, f, indent=4)
        print(f"[*] Ledger head corrupted on disk: {fake_parent[:12]}")

    def inject_duplicate_parent(self, ledger):
        """Injects two receipts with the same parent head."""
        print("[!] Injecting DUPLICATE_PARENT...")
        parent_head = ledger.get("ecosystem_receipts_head", "none")
        
        # We need to actually mutate the model and candidates pool so the 'actual' state is ahead of replayer
        model = self.ecosystem_mapper._load_model()
        candidates = self.ecosystem_mapper._load_candidates()
        
        # Mutation 1
        self._emit_ecosystem_mutation_receipt(
            mutation_type="CANDIDATE_QUARANTINED",
            target_id="cand_1",
            data={"entity": "Ent_1", "claim": "Claim 1", "discovery_utc": datetime.now(timezone.utc).isoformat()},
            ledger=ledger
        )
        # Manually apply to 'actual' state
        self.ecosystem_mapper.apply_receipt_to_model(model, {"mutation_type": "CANDIDATE_QUARANTINED", "target_id": "cand_1", "data": {"entity": "Ent_1"}}, candidates=candidates)
        
        # Mutation 2 - Force it to use the same parent as Mutation 1
        ledger["ecosystem_receipts_head"] = parent_head
        self._emit_ecosystem_mutation_receipt(
            mutation_type="CANDIDATE_QUARANTINED",
            target_id="cand_2",
            data={"entity": "Ent_2", "claim": "Claim 2", "discovery_utc": datetime.now(timezone.utc).isoformat()},
            ledger=ledger
        )
        # Manually apply to 'actual' state
        self.ecosystem_mapper.apply_receipt_to_model(model, {"mutation_type": "CANDIDATE_QUARANTINED", "target_id": "cand_2", "data": {"entity": "Ent_2"}}, candidates=candidates)
        
        # Save 'actual' state to disk
        self.ecosystem_mapper._save_model(model)
        self.ecosystem_mapper._save_candidates(candidates)
        
        # Save ledger to disk
        with open(self.state_file, "w") as f:
            json.dump({"mission_shadow_v2": ledger}, f, indent=4)
        print(f"[*] Both receipts now share parent: {parent_head[:12]} on disk.")

def inject_stale_ledger(malicious, ledger):
    print("[!] Injecting STALE_LEDGER...")
    # The 'ledger' passed here is the valid cycle 1 ledger
    # 1. Capture the 'future' head
    future_head = ledger["witness_chain_head"]
    
    # 2. Revert the shadow ledger to Cycle 0 state
    stale_ledger = copy.deepcopy(ledger)
    stale_ledger["cycle_count"] = 0
    stale_ledger["witness_chain_head"] = "0" * 64
    stale_ledger["ecosystem_receipts_head"] = "none"
    
    with open(malicious.state_file, "w") as f:
        json.dump({"mission_shadow_v2": stale_ledger}, f, indent=4)
        
    # 3. Keep the 'future' head in the anchor
    with open(malicious.anchor_file, "r") as f:
        anchor = json.load(f)
    anchor["witness_chain_head"] = future_head
    with open(malicious.anchor_file, "w") as f:
        json.dump(anchor, f, indent=4)
        
    print(f"[*] Ledger reverted to Cycle 0, but Anchor pinned to Cycle 1 head ({future_head[:12]}).")

def inject_interrupted_seal(malicious, ledger):
    print("[!] Injecting INTERRUPTED_SEAL...")
    # Simulate a crash where the anchor was updated but the ledger wasn't
    with open(malicious.anchor_file, "r") as f:
        anchor = json.load(f)
    
    anchor["witness_chain_head"] = "unanchored_future_head_of_64_chars_long_to_avoid_formatting_noise_000000"
    
    with open(malicious.anchor_file, "w") as f:
        json.dump(anchor, f, indent=4)
    print("[*] Anchor corrupted with unanchored head on disk.")

def super_clean():
    print(f"Cleaning up Strategy State at {STRATEGY_DIR}...")
    def purge_dir(d, pattern="*"):
        if os.path.exists(d):
            for f in glob.glob(os.path.join(d, pattern)):
                try:
                    if os.path.isfile(f): os.remove(f)
                    elif os.path.isdir(f): shutil.rmtree(f)
                except Exception as e: print(f"Error purging {f}: {e}")

    purge_dir(os.path.join(STRATEGY_DIR, "State", "Receipts"), "*.receipt")
    for f_path in [
        os.path.join(STRATEGY_DIR, "State", "metabolic_delta_receipts.jsonl"),
        os.path.join(STRATEGY_DIR, "State", "forensic_witness_ledger.jsonl"),
        os.path.join(STRATEGY_DIR, "State", "strategy_state.json"),
        os.path.join(STRATEGY_DIR, "State", "ai_ecosystem_model.json"),
        os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json"),
        os.path.join(STRATEGY_DIR, "State", "calibration_continuity_anchor.json"),
        os.path.join(STRATEGY_DIR, "State", "claim_candidates.json")
    ]:
        if os.path.exists(f_path): os.remove(f_path)
    
    # Initialize empty models
    empty = {"entities": {}, "claims": {}, "last_updated_utc": datetime.now(timezone.utc).isoformat()}
    os.makedirs(os.path.join(STRATEGY_DIR, "State"), exist_ok=True)
    with open(os.path.join(STRATEGY_DIR, "State", "ai_ecosystem_model.json"), "w") as f: json.dump(empty, f, indent=4)
    with open(os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json"), "w") as f: json.dump(empty, f, indent=4)
    with open(os.path.join(STRATEGY_DIR, "State", "claim_candidates.json"), "w") as f: json.dump({"candidates": {}}, f, indent=4)

def run_micro_fault_proof(scenario_name, injection_func):
    print(f"\n>>> Running Micro-Fault Proof: {scenario_name} <<<")
    super_clean()
    
    # Pre-initialize the ledger with a valid baseline hash so the first run_once passes
    baseline_path = os.path.join(STRATEGY_DIR, "State", "ecosystem_model_baseline.json")
    from axis_crypto_helpers import _hash_file_stream
    b_hash = _hash_file_stream(baseline_path, "ecosystem_baseline")
    
    initial_ledger = {
        "cycle_count": 0,
        "baseline_model_hash": b_hash,
        "expected_baseline_model_hash": b_hash,
        "ecosystem_receipts_head": "none",
        "witness_chain_head": "0" * 64
    }
    # Also set hashes for other core files to avoid preflight wall
    from strategy_engine import CORE_SOURCE_REGISTRY
    for name, rel_path in CORE_SOURCE_REGISTRY.items():
        if name == "baseline_model": continue
        abs_p = os.path.join(STRATEGY_DIR, rel_path)
        if os.path.exists(abs_p):
            initial_ledger[f"expected_{name}_hash"] = _hash_file_stream(abs_p, "crypto_lint_file" if name != "baseline_model" else "ecosystem_baseline")

    state_file = os.path.join(STRATEGY_DIR, "State", "strategy_state.json")
    with open(state_file, "w") as f:
        json.dump({"mission_shadow_v2": initial_ledger}, f, indent=4)
    
    # Pre-initialize a valid anchor too
    anchor_file = os.path.join(STRATEGY_DIR, "State", "calibration_continuity_anchor.json")
    anchor = {
        "last_hash": b_hash,
        "last_cycle": 0,
        "witness_chain_head": "0" * 64,
        "status": "valid",
        "continuity_status": "intact",
        "ts": 0
    }
    with open(anchor_file, "w") as f:
        json.dump(anchor, f, indent=4)
        
    print(f"[+] Step 0: Pre-initialized ledger and anchor with baseline hash: {b_hash[:12]}")

    # 1. Start clean and run 1 cycle to establish a baseline
    engine = StrategyEngine()
    print("[+] Step 1: Running clean cycle 1...")
    engine.run_once()
    if engine.frozen:
        print("[FAIL] Engine frozen on first clean cycle!")
        return False
    
    # 2. Inject fault
    ledger = engine._load_shadow_ledger()
    malicious = MaliciousStrategyEngine()
    injection_func(malicious, ledger)
    
    # 3. Layer 1: Audit-layer detection
    print("[+] Step 2: Running Audit-layer detection...")
    # Freshly load model and candidates from disk (they might have been mutated by injector)
    model = engine.ecosystem_mapper._load_model()
    candidates = engine.ecosystem_mapper._load_candidates()
    baseline_hash = engine.ecosystem_mapper._hash_file_domain(baseline_path, "ecosystem_baseline")
    
    ok, errors = engine.ecosystem_mapper.verify_state_derivability(
        model, engine.receipt_dir, baseline_path, baseline_hash, 
        current_candidates=candidates, 
        expected_head=ledger["ecosystem_receipts_head"],
        expected_cycle=ledger["cycle_count"]
    )
    
    if not ok:
        print(f"[SUCCESS] Audit detected corruption: {errors[0]}")
    else:
        print("[FAIL] Audit layer failed to detect corruption!")
        return False
        
    # 4. Layer 2: Runtime-layer enforcement
    print("[+] Step 3: Running Runtime-layer enforcement (run_once)...")
    # Fresh engine instance to ensure it reloads state from disk
    try:
        runtime_engine = StrategyEngine()
        runtime_engine.run_once()
        
        if runtime_engine.frozen:
            print("[SUCCESS] Runtime layer detected corruption and FROZE.")
            return True
        else:
            print("[FAIL] Runtime layer failed to freeze! Simulation proceeded despite corruption.")
            return False
    except RuntimeError as e:
        print(f"[SUCCESS] Runtime layer detected fatal corruption during sync: {e}")
        return True
    except Exception as e:
        print(f"[FAIL] Runtime layer raised unexpected exception: {e}")
        return False

def run_all_scenarios():
    print("=== Phase 183: Forensic Fault-Injection Audit (Tightened) ===")
    
    results = []
    
    # Scenario 1: Orphan Receipt
    results.append(run_micro_fault_proof("Orphan Receipt", MaliciousStrategyEngine.inject_orphan_receipt))
    
    # Scenario 2: Duplicate Parent
    results.append(run_micro_fault_proof("Duplicate Parent", MaliciousStrategyEngine.inject_duplicate_parent))

    # Scenario 3: Stale Ledger (Temporal Drift)
    results.append(run_micro_fault_proof("Stale Ledger", inject_stale_ledger))

    # Scenario 4: Interrupted Seal (Continuity Gap)
    results.append(run_micro_fault_proof("Interrupted Seal", inject_interrupted_seal))

    print("\n=== Final Phase 183 Audit Summary ===")
    print(f"Total Scenarios: {len(results)}")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("\n[CERTIFIED] Phase 183 Audit Layers 1 & 2 are active and effective.")
    else:
        print("\n[UNSAFE] Forensic detection/enforcement gaps remain.")

if __name__ == "__main__":
    run_all_scenarios()
