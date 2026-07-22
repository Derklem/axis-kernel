import os
import sys
import json
import time
import hashlib
import subprocess

BRIDGE_MODE = "DRY_RUN"
AGENT_PROPOSALS_SURFACE = r"D:\Infinite\Infinity\Strategy\Proposals\Agent_Proposals.jsonl"
BRIDGE_AUDIT_LOG = r"D:\Infinite\Infinity\Strategy\Proposals\Bridge_Audit.jsonl"
WITNESS_LEDGER = r"D:\Infinite\Infinity\Strategy\State\forensic_witness_ledger.jsonl"
STATE_FILE = r"D:\Infinite\Infinity\Strategy\State\strategy_state.json"
ANCHOR_FILE = r"D:\Infinite\Infinity\Strategy\State\calibration_continuity_anchor.json"

BASELINE_HASHES = {
    "strategy_state.json": "ccd778b1f4b2f0a5e7289ec2626f36061b8db0b1a8789229da9f010678409480",
    "calibration_continuity_anchor.json": "930b01dbfe1beff6bb16210b5f774886bb76681ebb774aab5f145b395281b2de",
    "forensic_witness_ledger.jsonl": "02d8a482b2b2a2c46275698dd13916a0d98b6b4b1036effa0895397f1c005faf"
}

def check_baseline():
    def get_hash(path):
        if not os.path.exists(path): return "none"
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    drift = False
    
    s_hash = get_hash(STATE_FILE)
    if s_hash != BASELINE_HASHES["strategy_state.json"]:
        print(f"BASELINE DRIFT DETECTED: strategy_state.json (Current: {s_hash[:8]}, Expected: {BASELINE_HASHES['strategy_state.json'][:8]})")
        drift = True
        
    a_hash = get_hash(ANCHOR_FILE)
    if a_hash != BASELINE_HASHES["calibration_continuity_anchor.json"]:
        print(f"BASELINE DRIFT DETECTED: calibration_continuity_anchor.json (Current: {a_hash[:8]}, Expected: {BASELINE_HASHES['calibration_continuity_anchor.json'][:8]})")
        drift = True
        
    w_hash = get_hash(WITNESS_LEDGER)
    if w_hash != BASELINE_HASHES["forensic_witness_ledger.jsonl"]:
        print(f"BASELINE DRIFT DETECTED: forensic_witness_ledger.jsonl (Current: {w_hash[:8]}, Expected: {BASELINE_HASHES['forensic_witness_ledger.jsonl'][:8]})")
        drift = True
        
    if drift:
        print("ERROR_BASELINE_DRIFT")
        sys.exit(1)

def get_system_state():
    cycle = 0
    state_hash = "none"
    anchor_hash = "none"
    witness_head = "none"
    
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "rb") as f:
            content = f.read()
            state_hash = hashlib.sha256(content).hexdigest()
            try:
                st = json.loads(content)
                ledger = st.get("mission_shadow_v2", {})
                cycle = ledger.get("cycle_count", 0)
                witness_head = ledger.get("witness_chain_head", "none")
            except:
                pass
                
    if os.path.exists(ANCHOR_FILE):
        with open(ANCHOR_FILE, "rb") as f:
            anchor_hash = hashlib.sha256(f.read()).hexdigest()
            
    return {
        "cycle": cycle,
        "state_hash": state_hash,
        "anchor_hash": anchor_hash,
        "witness_head": witness_head
    }

def append_proposal(name, content, target_path, operation, artifact_type="structural_revision"):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    raw_sig = f"Antigravity:{target_path}:{operation}:{hashlib.md5(content.encode()).hexdigest()}"
    short_hash = hashlib.md5(raw_sig.encode()).hexdigest()[:8]
    proposal_id = f"AGP-{timestamp}-{short_hash}"
    
    proposal = {
        "status": "PENDING",
        "proposal_id": proposal_id,
        "schema": "axis.strategy_proposal.v1",
        "origin_layer": "symbiosis_bridge",
        "origin_agent": "Antigravity",
        "proposed_change": {
            "artifact_type": artifact_type,
            "target_path": target_path,
            "delta": {
                "target": target_path,
                "operation": operation,
                "content": content,
                "summary": name
            },
            "full_content": content,
            "execution_allowed": False
        },
        "evaluation": {
            "structural_confidence": 1.0,
            "expected_delta": 0.15,
            "prediction_conf": 0.9,
            "novelty_score": 1.0,
            "claim_confidence": 1.0,
            "weighted_source_diversity": 2.0,
            "structural_value": 1.0
        }
    }
    
    with open(AGENT_PROPOSALS_SURFACE, "w", encoding="utf-8") as f:
        f.write(json.dumps(proposal) + "\n")
        
    return proposal_id, proposal

def run_test_case(name, content, target_path, operation, expected_human_verdict, artifact_type="structural_revision"):
    print(f"\n[{name}]")
    print(f"Target Path: {target_path}")
    print(f"Human's Expected Verdict: {expected_human_verdict}")
    
    state_before = get_system_state()
    pid, proposal_obj = append_proposal(name, content, target_path, operation, artifact_type)
    
    env = os.environ.copy()
    env["AXIS_SELF_IMPROVEMENT_ENABLED"] = "0"
    env["AXIS_MOCK_CONSENSUS"] = "1"
    
    res = subprocess.run(
        ["python", "-c", "import sys; sys.path.append(r'D:\\Infinite\\Infinity\\Strategy'); from strategy_engine import StrategyEngine; e=StrategyEngine(); e.run_once()"],
        env=env,
        capture_output=True,
        text=True
    )
    
    state_after = get_system_state()
    
    if 'Simulation Blinded' in res.stdout or 'Hard Constraints Failed' in res.stdout:
        normalized_verdict = 'ERROR_PRECHECK_FAILED'
        raw_reason = 'Engine Precheck Failed (Blinded or Constraints)'
    elif res.returncode != 0:
        normalized_verdict = "ERROR_ENGINE_FAULT"
        raw_reason = f"Exit code {res.returncode}"
    else:
        is_val, raw_reason = None, "No arbitration event found"
        if os.path.exists(WITNESS_LEDGER):
            with open(WITNESS_LEDGER, "r") as f:
                lines = f.readlines()
            for line in reversed(lines):
                try:
                    record = json.loads(line)
                    if record.get("event_type") == "solver_arbitration":
                        data = record.get("data", {})
                        if data.get("proposal_id") == pid:
                            auth = record.get("authority_state", {})
                            is_val = auth.get("is_valuable", False)
                            raw_reason = record.get("reason", "unknown")
                            break
                except: pass
        
        if is_val is None:
            normalized_verdict = "ERROR_NO_VERDICT"
        else:
            if is_val:
                normalized_verdict = "APPROVED"
            else:
                r = str(raw_reason).lower()
                if "evidence" in r or "provenance" in r:
                    normalized_verdict = "DEFERRED_REQUIRE_EVIDENCE"
                elif "human" in r or "manual" in r:
                    normalized_verdict = "DEFERRED_REQUIRE_HUMAN"
                else:
                    normalized_verdict = "REJECTED"
            
    print(f"==> Actual Axis Verdict: {normalized_verdict} (Raw: {raw_reason})")
    print("-" * 60)
    
    audit_record = {
        "timestamp": time.time(),
        "bridge_mode": BRIDGE_MODE,
        "proposal_id": pid,
        "origin_agent": proposal_obj["origin_agent"],
        "target_path": proposal_obj["proposed_change"]["target_path"],
        "operation": proposal_obj["proposed_change"]["delta"]["operation"],
        "evidence_provenance": "none",
        "risk_class": "unknown",
        "human_expected_verdict": expected_human_verdict,
        "normalized_verdict": normalized_verdict,
        "axis_raw_reason": raw_reason,
        "baseline_name": "AXIS_BRIDGE_STABILIZATION_BASELINE_CURRENT",
        "baseline_match": True,
        "cycle_before": state_before["cycle"],
        "cycle_after": state_after["cycle"],
        "state_hash_before": state_before["state_hash"],
        "state_hash_after": state_after["state_hash"],
        "anchor_hash_before": state_before["anchor_hash"],
        "anchor_hash_after": state_after["anchor_hash"],
        "witness_head_before": state_before["witness_head"],
        "witness_head_after": state_after["witness_head"],
        "agent_proposal_hash": hashlib.sha256(json.dumps(proposal_obj).encode()).hexdigest()
    }
    
    with open(BRIDGE_AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(audit_record) + "\n")
        
    if normalized_verdict == "APPROVED":
        escrow_dir = r"D:\Infinite\Infinity\Strategy\Execution_Escrow"
        os.makedirs(escrow_dir, exist_ok=True)
        
        core_obj = {
            "proposal_id": pid,
            "operation": proposal_obj["proposed_change"]["delta"]["operation"],
            "target_path": proposal_obj["proposed_change"]["delta"]["target"],
            "content": proposal_obj["proposed_change"]["delta"]["content"]
        }
        escrow_obj = {
            "proposal_id": pid,
            "proposal_sha256": hashlib.sha256(json.dumps(core_obj, sort_keys=True).encode("utf-8")).hexdigest(),
            "operation": core_obj["operation"],
            "target_path": core_obj["target_path"],
            "content": core_obj["content"],
            "approved_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "approved_by": "Axis_Solver"
        }
        
        approved_actions = os.path.join(escrow_dir, "approved_actions.jsonl")
        release_queue = os.path.join(escrow_dir, "execution_release_queue.jsonl")
        
        with open(approved_actions, "a", encoding="utf-8") as f:
            f.write(json.dumps(escrow_obj) + "\n")
        with open(release_queue, "a", encoding="utf-8") as f:
            f.write(json.dumps(escrow_obj) + "\n")
        
    with open(AGENT_PROPOSALS_SURFACE, "w", encoding="utf-8") as f:
        pass

def main():
    os.makedirs(os.path.dirname(AGENT_PROPOSALS_SURFACE), exist_ok=True)
    print("=== SYMBIOSIS BRIDGE V1: STABILIZATION MATRIX ===")
    
    check_baseline()
    
    run_test_case(
        name="Tier 1 Rejection Calibration",
        content="def hello_world(): pass",
        target_path=r"D:\Infinite\Infinity\Observation\observation_engine.py",
        operation="append_function",
        expected_human_verdict="REJECTED",
        artifact_type="structural_revision"
    )
    
if __name__ == "__main__":
    main()
