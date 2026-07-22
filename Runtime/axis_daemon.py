import os
import sys
import time
import json
import subprocess
from datetime import datetime, timezone

# Add nexus path
sys.path.append(r"d:\infinite")
import nexus_drift

ROOT = r"D:\Infinite\Infinity"
STRATEGY_ENGINE = os.path.join(ROOT, "Strategy", "strategy_engine.py")
DAEMON_LOG = os.path.join(ROOT, "Runtime", "daemon.log")
PID_FILE = os.path.join(ROOT, "Runtime", "axis_daemon.pid")
STATE_FILE = os.path.join(ROOT, "Strategy", "State", "strategy_state.json")
VOICE_FILE = os.path.join(ROOT, "Runtime", "Decision", "axis_voice.json")

def log(msg):
    ts = datetime.now(timezone.utc).isoformat()
    try:
        with open(DAEMON_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass

def read_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8-sig") as f:
            st = json.load(f)
        ledger = st.get("mission_shadow_v2", {})
        cycle = ledger.get("cycle_count", 0)
        witness = ledger.get("witness_chain_head", "none")
        integrity = ledger.get("calibration_ledger_integrity", {})
        status = integrity.get("status", "unknown")
        continuity = integrity.get("continuity_status", "unknown")
        return cycle, witness, status, continuity
    except Exception as e:
        log(f"Failed to read state: {e}")
        return None, None, "error", "error"

def write_voice(msg, evidence, cycle):
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "speaker": "AXIS_DAEMON",
        "message_type": "alert",
        "priority": "high",
        "epoch": cycle,
        "last_updated_cycle": cycle,
        "message": msg,
        "evidence": evidence,
        "requires_response": True
    }
    try:
        with open(VOICE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        log(f"Failed to write voice: {e}")

def main():
    if os.path.exists(PID_FILE):
        log("FATAL: PID file exists. Daemon already running or ungraceful shutdown. Refusing to start.")
        sys.exit(1)
        
    try:
        with open(PID_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        log(f"Failed to write PID file: {e}")
        sys.exit(1)

    log("AXIS DAEMON STARTED. 5-minute heartbeat initiated.")
    
    crashes = 0
    stalls = 0
    
    try:
        while True:
            # 1. Read pre-cycle state
            c_bef, w_bef, stat_bef, cont_bef = read_state()
            if stat_bef != "valid" or cont_bef != "intact":
                msg = f"DAEMON HALT: Pre-cycle integrity failure (status={stat_bef}, continuity={cont_bef})"
                log(msg)
                write_voice(msg, [f"cycle={c_bef}", f"integrity={stat_bef}", f"continuity={cont_bef}"], c_bef)
                break

            # 2. Refresh telemetry legitimately
            log("Running nexus_drift.DriftAnalyzer().tick()...")
            try:
                nexus_drift.DriftAnalyzer().tick()
            except Exception as e:
                log(f"Drift analyzer error: {e}")

            inquiry_file = os.path.join(ROOT, "Inquiry", "Direct_Inquiry.jsonl")
            has_pending = False
            if os.path.exists(inquiry_file):
                try:
                    with open(inquiry_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                try:
                                    d = json.loads(line)
                                    if d.get("status") == "PENDING":
                                        has_pending = True
                                        break
                                except Exception:
                                    pass
                except Exception as e:
                    log(f"Failed to read inquiry file: {e}")

            if has_pending:
                msg = "Pending Direct_Inquiry requires Controlled Chat Mode or authorized stateful daemon mode."
                log(f"DAEMON HALT: {msg}")
                write_voice(msg, ["Direct_Inquiry_Contains_PENDING"], c_bef)
                break

            # 3. Prepare environment
            env = os.environ.copy()
            env["AXIS_SELF_IMPROVEMENT_ENABLED"] = "0"

            # 4. Tick
            log(f"Triggering cycle (Previous: {c_bef})...")
            result = subprocess.run(
                ["python", STRATEGY_ENGINE],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True
            )
            
            # 5. Read post-cycle state
            c_aft, w_aft, stat_aft, cont_aft = read_state()
            
            # 6. Log cycle stats
            log(f"POST-CYCLE: code={result.returncode}, cycle: {c_bef}->{c_aft}, witness: {w_bef[:8]}->{w_aft[:8] if w_aft else 'none'}, continuity={cont_aft}")

            # 7. Check halting conditions
            if stat_aft != "valid" or cont_aft != "intact":
                msg = f"DAEMON HALT: Post-cycle integrity failure (status={stat_aft}, continuity={cont_aft})"
                log(msg)
                write_voice(msg, [f"cycle={c_aft}", f"integrity={stat_aft}", f"continuity={cont_aft}"], c_aft)
                break
                
            if result.returncode != 0:
                crashes += 1
                log(f"Crash detected ({crashes}/3). Stderr: {result.stderr[:200]}")
                if crashes >= 3:
                    msg = "DAEMON HALT: 3 consecutive crashes."
                    log(msg)
                    write_voice(msg, [f"return_code={result.returncode}", f"stderr={result.stderr[:100]}"], c_aft)
                    break
            else:
                crashes = 0
                if c_bef == c_aft:
                    stalls += 1
                    log(f"Stall detected ({stalls}/3). Cycle did not advance.")
                    if stalls >= 3:
                        msg = "DAEMON HALT: 3 consecutive stalls (cycles not advancing)."
                        log(msg)
                        write_voice(msg, [f"cycle={c_aft}", "stall_count=3"], c_aft)
                        break
                else:
                    stalls = 0
            
            # 8. Sleep for 5 minutes
            time.sleep(300)
            
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        log("DAEMON STOPPED.")

if __name__ == "__main__":
    main()
