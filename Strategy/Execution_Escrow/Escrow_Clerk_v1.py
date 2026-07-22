import os
import sys
import json
import time
import hashlib
import argparse

ESCROW_DIR = r"D:\Infinite\Infinity\Strategy\Execution_Escrow"
QUEUE_FILE = os.path.join(ESCROW_DIR, "execution_release_queue.jsonl")
RECEIPTS_FILE = os.path.join(ESCROW_DIR, "execution_receipts.jsonl")
DENIALS_FILE = os.path.join(ESCROW_DIR, "execution_denials.jsonl")
REGISTRY_FILE = os.path.join(ESCROW_DIR, "Execution_Capability_Registry.json")
BRIDGE_METADATA = r"D:\Infinite\Infinity\Strategy\Proposals\Bridge_Baseline_Metadata.json"

def get_hash(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def check_baseline():
    if not os.path.exists(BRIDGE_METADATA):
        print("ERROR: Baseline metadata missing.")
        return False
        
    with open(BRIDGE_METADATA, "r", encoding="utf-8") as f:
        metadata = json.load(f)
        
    hashes = metadata.get("hashes", {})
    for path, expected in hashes.items():
        if path == "strategy_state.json":
            actual = get_hash(r"D:\Infinite\Infinity\Strategy\State\strategy_state.json")
        elif path == "calibration_continuity_anchor.json":
            actual = get_hash(r"D:\Infinite\Infinity\Strategy\State\calibration_continuity_anchor.json")
        elif path == "forensic_witness_ledger.jsonl":
            actual = get_hash(r"D:\Infinite\Infinity\Strategy\State\forensic_witness_ledger.jsonl")
        else:
            continue
            
        if actual != expected:
            print(f"BASELINE DRIFT DETECTED: {path} (Current: {str(actual)[:8]}, Expected: {expected[:8]})")
            return False
            
    return True

def load_queue():
    queue = []
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    queue.append(json.loads(line))
    return queue

def save_queue(queue):
    os.makedirs(ESCROW_DIR, exist_ok=True)
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        for item in queue:
            f.write(json.dumps(item) + "\n")

def list_queue():
    queue = load_queue()
    print(f"=== EXECUTION ESCROW QUEUE ({len(queue)} pending) ===")
    for item in queue:
        print(f"[{item['proposal_id']}] {item['operation']} -> {item['target_path']}")

def process_proposal(proposal_id, action):
    queue = load_queue()
    proposal = next((p for p in queue if p["proposal_id"] == proposal_id), None)
    
    if not proposal:
        print(f"ERROR: Proposal {proposal_id} not found in release queue.")
        sys.exit(1)
        
    if action in ("release", "execute"):
        registry = None
        registry_status = "ok"
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except Exception:
            registry_status = "missing_or_malformed"
            
        operation = proposal["operation"]
        cap = registry.get(operation, {}) if registry else {}
        is_enabled = cap.get("enabled", False)
        
        if not registry or not cap or not is_enabled:
            reason_status = "disabled" if cap else registry_status if not registry else "unknown"
            denial = {
                "proposal_id": proposal["proposal_id"],
                "denied_by": "operator",
                "denied_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "reason": "capability_registry_denial",
                "capability": operation,
                "registry_status": reason_status
            }
            if proposal.get("drill"):
                denial["drill"] = True
            with open(DENIALS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(denial) + "\n")
                
            queue = [p for p in queue if p["proposal_id"] != proposal_id]
            save_queue(queue)
            
            print(f"ERROR: Execution capability blocked ({operation}). Automatic denial recorded.")
            sys.exit(1)
            
        if not check_baseline():
            denial = {
                "proposal_id": proposal["proposal_id"],
                "denied_by": "operator",
                "denied_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "reason": "baseline_drift_denial",
                "capability": operation,
                "registry_status": "enabled"
            }
            if proposal.get("drill"):
                denial["drill"] = True
            with open(DENIALS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(denial) + "\n")
            queue = [p for p in queue if p["proposal_id"] != proposal_id]
            save_queue(queue)
            print("ERROR: Execution blocked due to baseline drift. Automatic denial recorded.")
            sys.exit(1)
            
        core_obj = {
            "proposal_id": proposal["proposal_id"],
            "operation": proposal["operation"],
            "target_path": proposal["target_path"],
            "content": proposal["content"]
        }
        expected_hash = hashlib.sha256(json.dumps(core_obj, sort_keys=True).encode("utf-8")).hexdigest()
        
        if proposal.get("proposal_sha256") != expected_hash:
            denial = {
                "proposal_id": proposal["proposal_id"],
                "denied_by": "operator",
                "denied_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "reason": "proposal_hash_mismatch",
                "capability": operation,
                "registry_status": "enabled"
            }
            if proposal.get("drill"):
                denial["drill"] = True
            with open(DENIALS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(denial) + "\n")
            queue = [p for p in queue if p["proposal_id"] != proposal_id]
            save_queue(queue)
            print("ERROR: Proposal hash mismatch! Escrow record has been tampered with. Automatic denial recorded.")
            sys.exit(1)
            
        if action == "execute":
            # --- PHASE F2 / F2.5: TRUST PROFILE ENFORCEMENT ---
            TRUST_PROFILE_PATH = r"D:\Infinite\Infinity\Trust\Trust_Profile.json"
            if not os.path.exists(TRUST_PROFILE_PATH):
                denial = {
                    "proposal_id": proposal["proposal_id"],
                    "denied_by": "operator",
                    "denied_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "reason": "trust_profile_missing",
                    "capability": operation,
                    "registry_status": "enabled"
                }
                if proposal.get("drill"):
                    denial["drill"] = True
                with open(DENIALS_FILE, "a", encoding="utf-8") as f:
                        f.write(json.dumps(denial) + "\n")
                queue = [p for p in queue if p["proposal_id"] != proposal_id]
                save_queue(queue)
                print("ERROR: Execution aborted. Trust Profile is missing.")
                sys.exit(1)
                
            try:
                with open(TRUST_PROFILE_PATH, "r", encoding="utf-8") as f:
                    trust_profile = json.load(f)
            except Exception:
                denial = {
                    "proposal_id": proposal["proposal_id"],
                    "denied_by": "operator",
                    "denied_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "reason": "trust_profile_malformed",
                    "capability": operation,
                    "registry_status": "enabled"
                }
                if proposal.get("drill"):
                    denial["drill"] = True
                with open(DENIALS_FILE, "a", encoding="utf-8") as f:
                        f.write(json.dumps(denial) + "\n")
                queue = [p for p in queue if p["proposal_id"] != proposal_id]
                save_queue(queue)
                print("ERROR: Execution aborted. Trust Profile is malformed.")
                sys.exit(1)
                
            gen_utc_str = trust_profile.get("trust_profile_generated_utc")
            if not gen_utc_str:
                denial = {
                    "proposal_id": proposal["proposal_id"],
                    "denied_by": "operator",
                    "denied_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "reason": "trust_profile_missing_generated_utc",
                    "capability": operation,
                    "registry_status": "enabled"
                }
                if proposal.get("drill"):
                    denial["drill"] = True
                with open(DENIALS_FILE, "a", encoding="utf-8") as f:
                        f.write(json.dumps(denial) + "\n")
                queue = [p for p in queue if p["proposal_id"] != proposal_id]
                save_queue(queue)
                print("ERROR: Execution aborted. Trust Profile missing generated_utc.")
                sys.exit(1)
                
            try:
                import datetime
                gen_time = datetime.datetime.strptime(gen_utc_str, "%Y-%m-%dT%H:%M:%SZ")
                now_utc = datetime.datetime.utcnow()
                age_minutes = (now_utc - gen_time).total_seconds() / 60.0
                if age_minutes > 15:
                    denial = {
                        "proposal_id": proposal["proposal_id"],
                        "denied_by": "operator",
                        "denied_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "reason": "trust_profile_stale",
                        "capability": operation,
                        "registry_status": "enabled"
                    }
                    with open(DENIALS_FILE, "a", encoding="utf-8") as f:
                        f.write(json.dumps(denial) + "\n")
                    queue = [p for p in queue if p["proposal_id"] != proposal_id]
                    save_queue(queue)
                    print(f"ERROR: Execution aborted. Trust Profile is stale ({age_minutes:.1f} minutes old).")
                    sys.exit(1)
            except Exception as e:
                denial = {
                    "proposal_id": proposal["proposal_id"],
                    "denied_by": "operator",
                    "denied_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "reason": "trust_profile_generated_utc_parse_failure",
                    "capability": operation,
                    "registry_status": "enabled"
                }
                if proposal.get("drill"):
                    denial["drill"] = True
                with open(DENIALS_FILE, "a", encoding="utf-8") as f:
                        f.write(json.dumps(denial) + "\n")
                queue = [p for p in queue if p["proposal_id"] != proposal_id]
                save_queue(queue)
                print(f"ERROR: Execution aborted. Failed to parse generated_utc: {e}")
                sys.exit(1)
                
            trust_pressure = trust_profile.get("trust_pressure")
            if trust_pressure == "execution_freeze_recommended":
                denial = {
                    "proposal_id": proposal["proposal_id"],
                    "denied_by": "operator",
                    "denied_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "reason": "trust_pressure_freeze_denial",
                    "capability": operation,
                    "registry_status": "enabled"
                }
                if proposal.get("drill"):
                    denial["drill"] = True
                with open(DENIALS_FILE, "a", encoding="utf-8") as f:
                        f.write(json.dumps(denial) + "\n")
                queue = [p for p in queue if p["proposal_id"] != proposal_id]
                save_queue(queue)
                print("ERROR: Execution aborted. Trust pressure at execution_freeze_recommended.")
                sys.exit(1)
            # --- END PHASE F2 / F2.5 ---
            
            # --- PHASE F5: EPISTEMIC CHALLENGE ENFORCEMENT ---
            CHALLENGES_FILE = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_challenges.jsonl"
            DEFENSES_FILE = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_defenses.jsonl"
            
            challenge_rec = None
            defense_rec = None
            
            if os.path.exists(CHALLENGES_FILE):
                with open(CHALLENGES_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip(): continue
                        try:
                            c = json.loads(line)
                            if c.get("proposal_id") == proposal_id: challenge_rec = c
                        except: pass
                        
            if os.path.exists(DEFENSES_FILE):
                with open(DEFENSES_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip(): continue
                        try:
                            d = json.loads(line)
                            if d.get("proposal_id") == proposal_id: defense_rec = d
                        except: pass
                        
            if not (challenge_rec and defense_rec):
                denial = {
                    "proposal_id": proposal["proposal_id"],
                    "denied_by": "operator",
                    "denied_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "reason": "epistemic_challenge_unanswered",
                    "capability": operation,
                    "registry_status": "enabled"
                }
                if proposal.get("drill"):
                    denial["drill"] = True
                with open(DENIALS_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(denial) + "\n")
                queue = [p for p in queue if p["proposal_id"] != proposal_id]
                save_queue(queue)
                print("ERROR: Execution aborted. Missing required Epistemic Challenge Receipt or Defense Receipt.")
                sys.exit(1)
                
            bind_c_hash = challenge_rec.get("proposal_sha256") == proposal.get("proposal_sha256")
            bind_d_hash = defense_rec.get("proposal_sha256") == proposal.get("proposal_sha256")
            bind_c_id = defense_rec.get("challenge_id") == challenge_rec.get("challenge_id")
            
            if not (bind_c_hash and bind_d_hash and bind_c_id):
                denial = {
                    "proposal_id": proposal["proposal_id"],
                    "denied_by": "operator",
                    "denied_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "reason": "epistemic_receipt_binding_mismatch",
                    "capability": operation,
                    "registry_status": "enabled"
                }
                if proposal.get("drill"):
                    denial["drill"] = True
                with open(DENIALS_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(denial) + "\n")
                queue = [p for p in queue if p["proposal_id"] != proposal_id]
                save_queue(queue)
                print("ERROR: Execution aborted. Epistemic bindings mismatched. Tampering or stale defense detected.")
                sys.exit(1)
            # --- END PHASE F5 ---

            if operation != "create_report":
                denial = {
                    "proposal_id": proposal["proposal_id"],
                    "denied_by": "operator",
                    "denied_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "reason": "c0_operation_denial",
                    "capability": operation,
                    "registry_status": "enabled"
                }
                if proposal.get("drill"):
                    denial["drill"] = True
                with open(DENIALS_FILE, "a", encoding="utf-8") as f:
                        f.write(json.dumps(denial) + "\n")
                queue = [p for p in queue if p["proposal_id"] != proposal_id]
                save_queue(queue)
                print(f"ERROR: Execution aborted. Operation '{operation}' not permitted for materialization.")
                sys.exit(1)
                
            reports_root = os.path.abspath(r"D:\Infinite\Infinity\Reports")
            target_abs = os.path.abspath(proposal["target_path"])
            
            if target_abs == reports_root or not target_abs.startswith(reports_root + os.sep):
                denial = {
                    "proposal_id": proposal["proposal_id"],
                    "denied_by": "operator",
                    "denied_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "reason": "c0_path_boundary_denial",
                    "capability": operation,
                    "registry_status": "enabled"
                }
                if proposal.get("drill"):
                    denial["drill"] = True
                with open(DENIALS_FILE, "a", encoding="utf-8") as f:
                        f.write(json.dumps(denial) + "\n")
                queue = [p for p in queue if p["proposal_id"] != proposal_id]
                save_queue(queue)
                print(f"ERROR: Execution aborted. Target path '{proposal['target_path']}' is outside permitted boundary.")
                sys.exit(1)
                
            if not target_abs.lower().endswith(".md"):
                denial = {
                    "proposal_id": proposal["proposal_id"],
                    "denied_by": "operator",
                    "denied_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "reason": "c0_extension_denial",
                    "capability": operation,
                    "registry_status": "enabled"
                }
                if proposal.get("drill"):
                    denial["drill"] = True
                with open(DENIALS_FILE, "a", encoding="utf-8") as f:
                        f.write(json.dumps(denial) + "\n")
                queue = [p for p in queue if p["proposal_id"] != proposal_id]
                save_queue(queue)
                print(f"ERROR: Execution aborted. Extension must be .md")
                sys.exit(1)
                
            if os.path.exists(target_abs):
                base, ext = os.path.splitext(target_abs)
                candidate_path = base + ".candidate" + ext
                final_path = candidate_path
            else:
                final_path = target_abs
                
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            content = proposal["content"]
            with open(final_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            bytes_written = len(content.encode("utf-8"))

        receipt_id = f"RCPT-{time.strftime('%Y%m%d-%H%M%S')}"
        receipt = {
            "proposal_id": proposal["proposal_id"],
            "operation": proposal["operation"],
            "target_path": proposal["target_path"],
            "content_sha256": hashlib.sha256(proposal["content"].encode("utf-8")).hexdigest(),
            "released_by": "operator",
            "released_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "receipt_id": receipt_id,
            "capability": operation,
            "capability_risk": cap.get("risk", "unknown"),
            "capability_registry_version": "v1"
        }
        
        if action == "execute":
            receipt["execution_performed"] = True
            receipt["phase"] = "C0_CONTROLLED_REPORT_MATERIALIZATION"
            receipt["materialized_path"] = final_path
            receipt["bytes_written"] = bytes_written
        else:
            receipt["execution_performed"] = False
            receipt["phase"] = cap.get("phase", "B_RECEIPT_ONLY")
            receipt["manual_execution_required"] = True
        
        if proposal.get("drill"):
            receipt["drill"] = True
        with open(RECEIPTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(receipt) + "\n")
            
        print(f"\n--- EXECUTION PACKAGE {'MATERIALIZED' if action == 'execute' else 'EMITTED'} ---")
        print(json.dumps(receipt, indent=2))
        print("---------------------------------")
        if action == "release":
            print("Phase B: Manual operator execution required.")
        
    elif action == "deny":
        denial = {
            "proposal_id": proposal["proposal_id"],
            "denied_by": "operator",
            "denied_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        if proposal.get("drill"):
            denial["drill"] = True
        with open(DENIALS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(denial) + "\n")
        print(f"Proposal {proposal_id} denied and recorded.")
        
    # Remove from queue
    queue = [p for p in queue if p["proposal_id"] != proposal_id]
    save_queue(queue)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execution Escrow Clerk")
    parser.add_argument("--list", action="store_true", help="List pending proposals")
    parser.add_argument("--release", type=str, help="Release a proposal (receipt-only)")
    parser.add_argument("--execute", type=str, help="Execute a proposal (materialize)")
    parser.add_argument("--deny", type=str, help="Deny a proposal")
    args = parser.parse_args()

    os.makedirs(ESCROW_DIR, exist_ok=True)
    
    if args.list:
        list_queue()
    elif args.release:
        process_proposal(args.release, "release")
    elif args.execute:
        process_proposal(args.execute, "execute")
    elif args.deny:
        process_proposal(args.deny, "deny")
    else:
        parser.print_help()
