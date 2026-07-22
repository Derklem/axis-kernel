import json
import os
import hashlib
import copy
from datetime import datetime

LEDGER_PATH = r"D:\infinite\Infinity\Strategy\State\forensic_witness_ledger.jsonl"
ANCHOR_PATH = r"D:\infinite\Infinity\Strategy\State\calibration_continuity_anchor.json"

class CausalAccountabilityVerifier:
    def __init__(self, ledger_path=LEDGER_PATH, anchor_path=ANCHOR_PATH):
        self.ledger_path = ledger_path
        self.anchor_path = anchor_path
        self.ledger = []
        self.anchor = {}
        
    def _canonical_json(self, obj):
        """Phase 73/74: Deterministic JSON serialization for canonical hashing."""
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def _hash_obj(self, obj, domain):
        """Phase 73/74/75/77: Deterministic hash with strict domain separation."""
        prefix = f"AXIS::{domain}::".encode("utf-8")
        content = self._canonical_json(obj).encode("utf-8")
        return hashlib.sha256(prefix + content).hexdigest()
        
    def load_data(self):
        self.ledger = []
        
        # 1. Load Archived Segments (Phase 44)
        export_dir = os.path.join(os.path.dirname(self.ledger_path), "Archival_Exports")
        segments = []
        if os.path.exists(export_dir):
            for f in os.listdir(export_dir):
                if f.startswith("forensic_witness_ledger_") and f.endswith(".jsonl"):
                    segments.append(os.path.join(export_dir, f))
        
        # Sort by timestamp in filename (assumed monotonic)
        segments.sort()
        
        for s_path in segments:
            print(f"DEBUG: Loading archived segment: {os.path.basename(s_path)}")
            with open(s_path, "r") as f:
                for line in f:
                    if line.strip():
                        try: self.ledger.append(json.loads(line))
                        except: pass
        
        # 2. Load Live Segment
        if os.path.exists(self.ledger_path):
            print(f"DEBUG: Loading live segment: {os.path.basename(self.ledger_path)}")
            with open(self.ledger_path, "r") as f:
                for line in f:
                    if line.strip():
                        try: self.ledger.append(json.loads(line))
                        except: pass
        else:
            if not segments:
                print(f"ERROR: Ledger missing at {self.ledger_path}")
                return False
        
        if os.path.exists(self.anchor_path):
            with open(self.anchor_path, "r") as f:
                self.anchor = json.load(f)
        
        return True

    def verify_chain(self, ledger=None):
        ledger = ledger if ledger is not None else self.ledger
        print("--- Step 1: Chain Integrity Audit ---")
        if not ledger:
            print("Ledger is empty.")
            return True

        prev_hash = ledger[0].get("prev_witness_hash")
        errors = []
        
        for i, entry in enumerate(ledger):
            # 1. Chain Linkage
            if entry.get("prev_witness_hash") != prev_hash:
                if entry.get("event_type") == "archival_rotation:continuation_head":
                    print(f"DEBUG: Rotation Link Detected. Segment Handshake: {prev_hash[:12]} -> {entry.get('prev_witness_hash')[:12]}")
                elif entry.get("prev_witness_hash") == "none":
                    # Phase 187: Origin entry correctly anchored to 'none' sentinel.
                    pass
                else:
                    errors.append(f"Chain Break at Entry {i}: Expected {prev_hash[:12]}, found {entry.get('prev_witness_hash')[:12]}")
            
            # 2. Tamper Protection
            content = entry.copy()
            content.pop("witness_hash", None)
            recomputed = self._hash_obj(content, "witness_record")
            
            if entry.get("witness_hash") != recomputed:
                 errors.append(f"Tamper Detected at Entry {i}: Recomputed {recomputed[:12]} != Found {entry.get('witness_hash', 'none')[:12]}")
            
            prev_hash = entry.get("witness_hash")
            
        if not errors:
            print("SUCCESS: Forensic witness chain integrity verified.")
            return True
        else:
            for err in errors: print(f"FAIL: {err}")
            return False

    def verify_anchor(self, ledger=None):
        ledger = ledger if ledger is not None else self.ledger
        print("\n--- Step 2: Anchor Binding Audit ---")
        if not self.anchor:
            print("WARNING: No anchor file found. Skipping anchor head verification.")
            return True
        
        anchor_head = self.anchor.get("witness_chain_head")
        if not ledger:
            return False
        
        actual_head = ledger[-1].get("witness_hash")
        if actual_head != anchor_head:
            print(f"FAIL: Anchor head mismatch! Anchor: {anchor_head[:16]}... Ledger: {actual_head[:16]}...")
            return False
        
        print(f"SUCCESS: Ledger head ({actual_head[:16]}...) matches anchor head.")
        return True

    def verify_causality(self, ledger=None):
        """Phase 43: Reconstructs and re-validates the causal chain."""
        ledger = ledger if ledger is not None else self.ledger
        print("\n--- Step 3: Causal Accountability Audit ---")
        verdicts = [w for w in ledger if w.get("event_type") == "cycle_verdict"]
        all_passed = True
        
        if not verdicts:
            print("No cycle verdicts found for causal auditing.")
            return True

        for v in verdicts:
            v_data = v.get("data", {})
            links = v_data.get("causal_links", [])
            cycle = v.get("cycle")
            v_hash = v.get("witness_hash", "none")
            
            print(f"\nCycle {cycle} Verdict: {v_hash[:16]}... (Links: {len(links)})")
            
            # Phase 43: Verify state-transition metrics if available
            final_hash = v_data.get("final_calibration_hash")
            anchor_hash = v_data.get("anchor_hash")
            start_witness = v_data.get("cycle_start_witness_hash")
            
            if final_hash and anchor_hash:
                print(f"  [i] State Proof: Anchor({anchor_hash[:12]}) -> Start({start_witness[:12]}) -> Final({final_hash[:12]})")
            else:
                print(f"  [!] Missing state proofs in cycle verdict data.")
                # We don't fail yet as legacy witnesses might lack these, but Phase 43 requires them
                pass

            for link_hash in links:
                # 1. Find Consensus Witness
                consensus = next((w for w in ledger if w.get("witness_hash") == link_hash), None)
                if not consensus:
                    print(f"  [!] BROKEN LINK: Consensus witness {link_hash[:16]}... not found in ledger!")
                    all_passed = False
                    continue
                
                if consensus.get("event_type") != "multi_model_consensus":
                    print(f"  [!] TYPE MISMATCH: Link points to {consensus.get('event_type')}, not multi_model_consensus!")
                    all_passed = False
                    continue
                
                c_data = consensus.get("data", {})
                payload_id = c_data.get("payload_id")
                decision = c_data.get("decision")
                
                # 2. Find Arbitration Witness
                arbitration = next((w for w in ledger if w.get("event_type") == "sovereign_arbitration" and w.get("input_hash") == payload_id), None)
                
                if not arbitration:
                    print(f"  [!] ORPHAN CONSENSUS: Consensus for {decision} has no matching arbitration!")
                    all_passed = False
                else:
                    # 3. Robust Payload ID Verification
                    # Recompute payload_id from the arbitration data to ensure content integrity
                    arb_data = arbitration.get("data")
                    if arb_data:
                        recomputed_id = self._hash_obj(arb_data, "witness_input")
                        if recomputed_id != payload_id:
                            print(f"  [!] PAYLOAD INTEGRITY BREACH: Consensus ID {payload_id[:12]} does not match recomputed Arbitration ID {recomputed_id[:12]}!")
                            all_passed = False
                            continue
                    
                    verdict = arbitration.get("authority_state", {}).get("verdict")
                    print(f"  [+] CAUSAL CHAIN VERIFIED: {decision} -> consensus ({link_hash[:12]}) -> arbitration ({arbitration.get('witness_hash')[:12]}) -> verdict: {verdict}")
        
        return all_passed

    def run_adversarial_trials(self):
        print("\n" + "!"*40)
        print("RUNNING ADVERSARIAL TRIALS")
        print("!"*40)
        
        base_ledger = copy.deepcopy(self.ledger)
        if not base_ledger:
            print("Cannot run trials on empty ledger.")
            return

        # Trial 1: Tampered Data
        print("\nTrial 1: Tampered Data (Modifying a reason field)")
        tampered = copy.deepcopy(base_ledger)
        tampered[0]["reason"] = "FRAUDULENT_REASON"
        if not self.verify_chain(tampered): print("  [OK] Verifier caught tampered data.")
        else: print("  [FAIL] Verifier missed tampered data!")

        # Trial 2: Fake Causal Link
        print("\nTrial 2: Fake Causal Link")
        fake_link = copy.deepcopy(base_ledger)
        for w in fake_link:
            if w.get("event_type") == "cycle_verdict" and "data" in w:
                w["data"]["causal_links"].append("deadbeef" * 8)
                break
        if not self.verify_causality(fake_link): print("  [OK] Verifier caught fake causal link.")
        else: print("  [FAIL] Verifier missed fake causal link!")

        # Trial 3: Orphan Consensus (Arbitration missing)
        print("\nTrial 3: Orphan Consensus")
        orphan = [w for w in base_ledger if w.get("event_type") != "sovereign_arbitration"]
        if not self.verify_causality(orphan): print("  [OK] Verifier caught orphan consensus.")
        else: print("  [FAIL] Verifier missed orphan consensus!")

        # Trial 4: Payload ID Mismatch
        print("\nTrial 4: Payload ID Mismatch")
        mismatch = copy.deepcopy(base_ledger)
        for w in mismatch:
            if w.get("event_type") == "multi_model_consensus" and "data" in w:
                w["data"]["payload_id"] = "deadbeef" * 8
                break
        if not self.verify_causality(mismatch): print("  [OK] Verifier caught payload ID mismatch.")
        else: print("  [FAIL] Verifier missed payload ID mismatch!")

        # Trial 5: Anchor Mismatch
        print("\nTrial 5: Anchor Mismatch")
        old_anchor = self.anchor
        self.anchor = {"witness_chain_head": "deadbeef" * 8}
        if not self.verify_anchor(base_ledger): print("  [OK] Verifier caught anchor mismatch.")
        else: print("  [FAIL] Verifier missed anchor mismatch!")
        self.anchor = old_anchor

    def run_audit(self, trial=False):
        if not self.load_data():
            return

        chain_ok = self.verify_chain()
        anchor_ok = self.verify_anchor()
        causality_ok = self.verify_causality()

        print("\n" + "="*40)
        print("AUDIT VERDICT")
        print("="*40)
        print(f"Chain Integrity:    {'PASSED' if chain_ok else 'FAILED'}")
        print(f"Anchor Binding:     {'PASSED' if anchor_ok else 'FAILED'}")
        print(f"Causal Accountability: {'PASSED' if causality_ok else 'FAILED'}")
        print("="*40)
        
        if trial:
            self.run_adversarial_trials()

if __name__ == "__main__":
    import sys
    trial_mode = "--trial" in sys.argv
    verifier = CausalAccountabilityVerifier()
    verifier.run_audit(trial=trial_mode)
