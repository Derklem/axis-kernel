import os, json, shutil, sys, time
from datetime import datetime, timezone

ROOT = r"D:\Infinite\Infinity"
STRATEGY = os.path.join(ROOT, "Strategy")
STATE = os.path.join(STRATEGY, "State")
COMM = os.path.join(ROOT, "Communication")
ENGINE = os.path.join(STRATEGY, "strategy_engine.py")
STATE_FILE = os.path.join(STATE, "strategy_state.json")
ANCHOR_FILE = os.path.join(STATE, "calibration_continuity_anchor.json")

stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
backup_dir = os.path.join(COMM, "ARCHIVE", "pre_axis_answer_inbox_" + stamp)
os.makedirs(backup_dir, exist_ok=True)
shutil.copy2(ENGINE, os.path.join(backup_dir, "strategy_engine.py"))

method = r'''
    def _answer_axis_inbox(self):
        """Simple Answer Layer - read-only synthesis from latest inbox context.

        No cycle. No ingestion. No refactor. No governance mutation.
        Produces a bounded posture answer from current ledger/anchor state.
        """
        import os, json, glob

        archive_dir = r"D:\Infinite\Infinity\Communication\ARCHIVE\TO_AXS_READ"
        latest_question = "No archived inquiry found."

        files = glob.glob(os.path.join(archive_dir, "*.json")) + glob.glob(os.path.join(archive_dir, "*.txt"))
        files.sort(key=lambda p: os.path.getmtime(p))

        if files:
            path = files[-1]
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    raw = f.read()
                try:
                    data = json.loads(raw)
                    latest_question = data.get("question") or data.get("message") or str(data)
                except Exception:
                    latest_question = raw[:500]
            except Exception as e:
                latest_question = f"Could not read latest inquiry: {e}"

        ledger = self._load_shadow_ledger()
        integrity = ledger.get("calibration_ledger_integrity", {})
        status = integrity.get("status", "unknown")
        continuity = integrity.get("continuity_status", "unknown")
        cycle = ledger.get("cycle_count", 0)
        witness = str(ledger.get("witness_chain_head", ""))[:16]
        receipts_head = str(ledger.get("ecosystem_receipts_head", "none"))[:16]

        if status == "valid" and continuity == "intact":
            answer = (
                f"Safest next posture after cycle {cycle}: passive observation. "
                "Keep self-improvement disabled. Permit read-only audits, inbox reads, and voice writes only. "
                "Do not resume ingestion, refactor, or autonomous mutation until bounded audits repeatedly pass."
            )
            priority = "normal"
        else:
            answer = (
                f"Safest next posture after cycle {cycle}: forensic stabilization. "
                f"Integrity={status}, continuity={continuity}. Do not run cycles or mutate state."
            )
            priority = "high"

        self._emit_axis_voice(
            message=answer,
            message_type="bounded_answer",
            priority=priority,
            evidence=[
                f"question={latest_question[:180]}",
                f"cycle={cycle}",
                f"integrity={status}",
                f"continuity={continuity}",
                f"witness_head={witness}",
                f"ecosystem_receipts_head={receipts_head}",
                "read_only_synthesis",
                "no_cycle",
                "no_governance_mutation"
            ],
            requires_response=True
        )

        return {
            "question": latest_question,
            "answer": answer,
            "cycle": cycle,
            "integrity": status,
            "continuity": continuity,
            "witness_head": witness
        }

'''

with open(ENGINE, "r", encoding="utf-8") as f:
    src = f.read()

if "def _answer_axis_inbox" not in src:
    marker = "    def _read_axis_inbox"
    if marker not in src:
        raise RuntimeError("_read_axis_inbox not found. Install inbox reader first.")
    src = src.replace(marker, method + marker, 1)
    with open(ENGINE, "w", encoding="utf-8") as f:
        f.write(src)
    print("Inserted _answer_axis_inbox.")
else:
    print("_answer_axis_inbox already present.")

import py_compile
py_compile.compile(ENGINE, doraise=True)
print("py_compile OK.")

sys.path.append(STRATEGY)
from axis_crypto_helpers import _hash_file_stream
from strategy_engine import StrategyEngine

with open(STATE_FILE, "r", encoding="utf-8-sig") as f:
    state = json.load(f)

ledger = state["mission_shadow_v2"]
new_engine_hash = _hash_file_stream(ENGINE, "crypto_lint_file")
ledger["expected_strategy_engine_hash"] = new_engine_hash

ledger.setdefault("recovery_history", []).append({
    "ts_utc": datetime.now(timezone.utc).isoformat(),
    "reason": "installed_manual_axis_answer_inbox_no_cycle",
    "backup_dir": backup_dir,
    "expected_strategy_engine_hash": new_engine_hash
})

engine = StrategyEngine()
new_cal_hash = engine._compute_calibration_hash(
    ledger,
    override_witness_head=ledger.get("witness_chain_head")
)
ledger["calibration_ledger_integrity"]["hash"] = new_cal_hash
ledger["calibration_ledger_integrity"]["status"] = "valid"
ledger["calibration_ledger_integrity"]["continuity_status"] = "intact"

state["mission_shadow_v2"] = ledger
with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=4, ensure_ascii=False)

with open(ANCHOR_FILE, "r", encoding="utf-8-sig") as f:
    anchor = json.load(f)
anchor["last_hash"] = new_cal_hash
anchor["status"] = "valid"
anchor["continuity_status"] = "intact"
anchor["ts"] = time.time()
with open(ANCHOR_FILE, "w", encoding="utf-8") as f:
    json.dump(anchor, f, indent=4, ensure_ascii=False)

print("Hash re-anchored.")
print("BACKUP:", backup_dir)
