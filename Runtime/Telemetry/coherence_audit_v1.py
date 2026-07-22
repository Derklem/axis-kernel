import os
import json
import sys

def audit_coherence():
    # File paths
    AGENT_PROPOSALS = r"D:\Infinite\Infinity\Strategy\Proposals\Agent_Proposals.jsonl"
    METRICS_FILE = r"D:\Infinite\Infinity\Runtime\Decision\Governance_Metrics.json"
    EXECUTOR_LEDGER = r"D:\Infinite\Infinity\Runtime\Executor\executor_fault_ledger.jsonl"
    WATCHDOG_LEDGER = r"D:\Infinite\Infinity\Runtime\Watchdog\watchdog_ledger.jsonl"
    INCIDENT_SNAPSHOT = r"D:\Infinite\Infinity\Runtime\Telemetry\incident_snapshot.jsonl"
    BRIDGE_METADATA = r"D:\Infinite\Infinity\Strategy\Proposals\Bridge_Baseline_Metadata.json"
    SYMBIOSIS_BRIDGE = r"D:\Infinite\Infinity\symbiosis_bridge.py"

    checks = []

    # 1. No pending proposals
    pending_count = 0
    if os.path.exists(AGENT_PROPOSALS):
        with open(AGENT_PROPOSALS, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        prop = json.loads(line)
                        if prop.get("status") == "PENDING":
                            pending_count += 1
                    except: pass
    if pending_count == 0:
        checks.append("[PASS] No pending proposals.")
    else:
        checks.append(f"[FAIL] Found {pending_count} pending proposals.")

    # 2. Oracle metrics parse & 3. Oracle provenance fields match current tier
    if os.path.exists(METRICS_FILE):
        try:
            with open(METRICS_FILE, "r", encoding="utf-8") as f:
                metrics = json.load(f)
            checks.append("[PASS] Oracle metrics parse correctly.")
            
            prov_fail = False
            for k, v in metrics.items():
                if k.endswith("_provenance"):
                    if "unobserved_conservative_fallback" in v and k != "mttr_p95_24h_provenance":
                        checks.append(f"[FAIL] Unexpected unobserved provenance: {k} = {v}")
                        prov_fail = True
            if not prov_fail:
                checks.append("[PASS] Oracle provenance fields match current tier.")
        except Exception as e:
            checks.append(f"[FAIL] Oracle metrics parsing failed: {e}")
    else:
        checks.append("[FAIL] Oracle metrics file missing.")

    # 4. Executor ledger has non-drill live rows
    if os.path.exists(EXECUTOR_LEDGER):
        has_live = False
        with open(EXECUTOR_LEDGER, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        rec = json.loads(line)
                        if not rec.get("drill"):
                            has_live = True
                            break
                    except: pass
        if has_live:
            checks.append("[PASS] Executor ledger has non-drill live rows.")
        else:
            checks.append("[FAIL] No non-drill live rows in executor ledger.")
    else:
        checks.append("[FAIL] Executor ledger missing.")

    # 5. Watchdog ledger has non-drill live rows
    if os.path.exists(WATCHDOG_LEDGER):
        has_live = False
        with open(WATCHDOG_LEDGER, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        rec = json.loads(line)
                        if not rec.get("drill"):
                            has_live = True
                            break
                    except: pass
        if has_live:
            checks.append("[PASS] Watchdog ledger has non-drill live rows.")
        else:
            checks.append("[FAIL] No non-drill live rows in watchdog ledger.")
    else:
        checks.append("[FAIL] Watchdog ledger missing.")

    # 6. Incident snapshot excludes drill from production MTTR
    if os.path.exists(INCIDENT_SNAPSHOT) and os.path.exists(METRICS_FILE):
        has_drill_incident = False
        with open(INCIDENT_SNAPSHOT, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        rec = json.loads(line)
                        if rec.get("drill"):
                            has_drill_incident = True
                            break
                    except: pass
        
        with open(METRICS_FILE, "r", encoding="utf-8") as f:
            metrics = json.load(f)
            
        mttr = metrics.get("mttr_p95_24h")
        if has_drill_incident and mttr == 999:
            checks.append("[PASS] Incident snapshot isolates drill from production MTTR.")
        else:
            checks.append(f"[FAIL] Incident snapshot drill isolation failed. MTTR={mttr}, has_drill={has_drill_incident}")
    else:
        checks.append("[FAIL] Incident snapshot or Metrics file missing for MTTR check.")

    # 7. Symbiosis bridge baseline matches current metadata
    if os.path.exists(BRIDGE_METADATA) and os.path.exists(SYMBIOSIS_BRIDGE):
        with open(BRIDGE_METADATA, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            meta_hashes = metadata.get("hashes", {})
            
        with open(SYMBIOSIS_BRIDGE, "r", encoding="utf-8") as f:
            bridge_content = f.read()
            
        bridge_match = True
        for fname, expected_hash in meta_hashes.items():
            if expected_hash not in bridge_content:
                bridge_match = False
                break
        
        if bridge_match:
            checks.append("[PASS] Symbiosis bridge baseline matches current metadata.")
        else:
            checks.append("[FAIL] Symbiosis bridge baseline mismatch with current metadata.")
    else:
        checks.append("[FAIL] Metadata or Bridge script missing.")

    # 8. All non-drill executed receipts must have a verification record
    EXECUTION_RECEIPTS = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\execution_receipts.jsonl"
    EXECUTION_VERIFICATION = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\execution_verification.jsonl"
    
    unverified_receipts = set()
    if os.path.exists(EXECUTION_RECEIPTS):
        with open(EXECUTION_RECEIPTS, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    rec = json.loads(line)
                    if rec.get("execution_performed") is True and not rec.get("drill"):
                        receipt_id = rec.get("receipt_id")
                        if receipt_id:
                            unverified_receipts.add(receipt_id)
                except: pass

    if os.path.exists(EXECUTION_VERIFICATION):
        with open(EXECUTION_VERIFICATION, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    rec = json.loads(line)
                    if not rec.get("drill"):
                        receipt_id = rec.get("receipt_id")
                        if receipt_id in unverified_receipts:
                            unverified_receipts.remove(receipt_id)
                except: pass

    if len(unverified_receipts) == 0:
        checks.append("[PASS] All non-drill executed receipts are verified.")
    else:
        checks.append(f"[FAIL] Found {len(unverified_receipts)} dangling unverified executed receipts.")

    # 9. Trust Profile and Advisory Pressure
    TRUST_PROFILE_FILE = r"D:\Infinite\Infinity\Trust\Trust_Profile.json"
    GEMINI_PACKET_FILE = r"D:\Infinite\gemini_packet.txt"
    
    if os.path.exists(TRUST_PROFILE_FILE):
        try:
            with open(TRUST_PROFILE_FILE, "r", encoding="utf-8") as f:
                profile = json.load(f)
            if profile.get("trust_mode") == "ADVISORY_ONLY":
                checks.append("[PASS] Trust Profile exists and is in ADVISORY_ONLY mode.")
            else:
                checks.append(f"[FAIL] Trust Profile is not ADVISORY_ONLY (found: {profile.get('trust_mode')})")
                
            expected_pressure = profile.get("trust_pressure", "UNKNOWN")
            
            if os.path.exists(GEMINI_PACKET_FILE):
                with open(GEMINI_PACKET_FILE, "r", encoding="utf-8") as f:
                    packet_content = f.read()
                if f"TRUST PRESSURE: {expected_pressure}" in packet_content:
                    checks.append("[PASS] Gemini packet correctly exposes TRUST PRESSURE.")
                else:
                    checks.append(f"[FAIL] Gemini packet does not contain expected TRUST PRESSURE: {expected_pressure}")
                    
                if "F6 DEFENSE QUALITY (ADVISORY)" in packet_content:
                    checks.append("[PASS] Gemini packet correctly exposes F6 Defense Quality telemetry.")
                else:
                    checks.append("[FAIL] Gemini packet does not contain F6 Defense Quality telemetry.")
            else:
                checks.append("[FAIL] gemini_packet.txt missing for trust exposure check.")
                
        except Exception as e:
            checks.append(f"[FAIL] Trust Profile parsing failed: {e}")
    else:
        checks.append("[FAIL] Trust_Profile.json is missing.")

    # 10. F2 Execution Freeze Enforcement Checks
    ESCROW_CLERK_FILE = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\Escrow_Clerk_v1.py"
    if os.path.exists(TRUST_PROFILE_FILE):
        try:
            with open(TRUST_PROFILE_FILE, "r", encoding="utf-8") as f:
                profile = json.load(f)
            
            gen_utc_str = profile.get("trust_profile_generated_utc")
            if gen_utc_str:
                checks.append("[PASS] Trust Profile contains trust_profile_generated_utc.")
                import datetime
                try:
                    gen_time = datetime.datetime.strptime(gen_utc_str, "%Y-%m-%dT%H:%M:%SZ")
                    now_utc = datetime.datetime.utcnow()
                    age_minutes = (now_utc - gen_time).total_seconds() / 60.0
                    if age_minutes <= 15:
                        checks.append("[PASS] Trust profile age is within 15 minutes.")
                    else:
                        checks.append(f"[FAIL] Trust profile is stale ({age_minutes:.1f} minutes old).")
                except Exception as e:
                    checks.append(f"[FAIL] Failed to parse generated_utc in audit: {e}")
            else:
                checks.append("[FAIL] Trust Profile missing trust_profile_generated_utc.")
        except Exception as e:
            checks.append(f"[FAIL] Trust Profile parsing failed in F2 check: {e}")
    else:
        checks.append("[FAIL] Trust_Profile.json is missing for F2 check.")

    if os.path.exists(ESCROW_CLERK_FILE):
        with open(ESCROW_CLERK_FILE, "r", encoding="utf-8") as f:
            clerk_content = f.read()
        
        if "trust_profile_stale" in clerk_content:
            checks.append("[PASS] Escrow Clerk contains trust_profile_stale denial path.")
        else:
            checks.append("[FAIL] Escrow Clerk missing trust_profile_stale denial path.")
            
        if "trust_pressure_freeze_denial" in clerk_content:
            checks.append("[PASS] Escrow Clerk contains trust_pressure_freeze_denial path.")
        else:
            checks.append("[FAIL] Escrow Clerk missing trust_pressure_freeze_denial path.")
    else:
        checks.append("[FAIL] Escrow_Clerk_v1.py missing for F2 check.")

    # 11. F8 Market Health Reports
    F8_REPORT_MD = r"D:\Infinite\Infinity\Reports\F8_Market_Health_Report.md"
    F8_REPORT_JSON = r"D:\Infinite\Infinity\Telemetry\F8_Market_Health_Report.json"
    
    if os.path.exists(F8_REPORT_MD) and os.path.exists(F8_REPORT_JSON):
        try:
            with open(F8_REPORT_JSON, "r", encoding="utf-8") as f:
                report = json.load(f)
            
            if "epistemic_state" in report and "integrity_state" in report:
                checks.append("[PASS] F8 Market Health reports exist and parse correctly.")
            else:
                checks.append("[FAIL] F8 Market Health JSON is malformed (missing required keys).")
        except Exception as e:
            checks.append(f"[FAIL] F8 Market Health JSON parsing failed: {e}")
    else:
        checks.append("[FAIL] F8 Market Health reports are missing.")

    print("\n--- TIER 2 COHERENCE AUDIT ---")
    all_pass = True
    for c in checks:
        print(c)
        if "[FAIL]" in c:
            all_pass = False
            
    if all_pass:
        print("\n=> AUDIT RESULT: COHERENT (Tier 2 sealed verified)")
        sys.exit(0)
    else:
        print("\n=> AUDIT RESULT: INCOHERENT")
        sys.exit(1)

if __name__ == "__main__":
    audit_coherence()
