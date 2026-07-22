import os, json, time, sys, hashlib
from datetime import datetime, timezone
import threading

ROOT = r"D:\Infinite\Infinity"
STATE = os.path.join(ROOT, "Strategy", "State")
CANDIDATES = os.path.join(STATE, "claim_candidates.json")
VOICE = os.path.join(ROOT, "Runtime", "Decision", "axis_voice.json")

def tail_voice():
    last_ts = None
    while True:
        try:
            if os.path.exists(VOICE):
                with open(VOICE, "r", encoding="utf-8-sig") as f:
                    v = json.load(f)
                ts = v.get("timestamp_utc")
                if ts != last_ts:
                    print(f"\n[AXIS at Epoch {v.get('epoch')}] ({v.get('priority')})")
                    print(f"> {v.get('message')}")
                    if v.get("evidence"):
                        print(f"Evidence: {', '.join(v.get('evidence')[:3])}")
                    last_ts = ts
                    print("\n[Operator] > ", end="", flush=True)
        except Exception:
            pass
        time.sleep(2)

def inject_directive(msg):
    try:
        with open(CANDIDATES, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception:
        data = {"candidates": {}, "cycle_count": 0}
        
    c_id = hashlib.sha256(msg.encode('utf-8')).hexdigest()
    data["candidates"][c_id] = {
        "entity": "operator_directive",
        "claim": f"[operator_directive] {msg}",
        "claim_domain": "operator_communication",
        "source_id": "OPERATOR",
        "source_type": "manual_injection",
        "artifact_type": "operator_directive",
        "batch_id": "none",
        "provenance_note": "Injected via Axis Terminal",
        "confidence": 1.0,
        "cycles_survived": 0,
        "discovery_utc": datetime.now(timezone.utc).isoformat(),
        "provenance_trail": []
    }
    
    tmp = CANDIDATES + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp, CANDIDATES)
    print(f"\n[System] Directive injected directly into Axis metabolism (Candidate ID: {c_id[:8]}).")

print("==================================================")
print("AXIS TERMINAL - DIRECT METABOLIC INJECTION")
print("==================================================")
print("Type your message. It will be injected directly as an actionable claim.")
print("Axis is fully unlocked. It will process this at its own pace.")
print("Type 'exit' to quit.")
print("==================================================\n")

t = threading.Thread(target=tail_voice, daemon=True)
t.start()

while True:
    try:
        msg = input("[Operator] > ")
        if msg.strip().lower() == 'exit':
            break
        if msg.strip():
            inject_directive(msg.strip())
    except KeyboardInterrupt:
        break
    except EOFError:
        break
