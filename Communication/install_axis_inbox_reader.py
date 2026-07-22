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
backup_dir = os.path.join(COMM, "ARCHIVE", "pre_axis_inbox_reader_" + stamp)
os.makedirs(backup_dir, exist_ok=True)
shutil.copy2(ENGINE, os.path.join(backup_dir, "strategy_engine.py"))

method = r'''
    def _read_axis_inbox(self, archive=True):
        """Simple Inbox Layer - Manual read of user messages from Communication\TO_AXS.

        This is intentionally non-actuating:
        - reads pending JSON/TXT messages
        - archives them if requested
        - emits a summary to axis_voice.json
        - does not run a cycle
        - does not mutate governance state
        """
        import os, json, shutil
        from datetime import datetime, timezone

        inbox = r"D:\Infinite\Infinity\Communication\TO_AXS"
        archive_dir = r"D:\Infinite\Infinity\Communication\ARCHIVE\TO_AXS_READ"
        os.makedirs(inbox, exist_ok=True)
        os.makedirs(archive_dir, exist_ok=True)

        files = []
        for name in os.listdir(inbox):
            path = os.path.join(inbox, name)
            if os.path.isfile(path) and (name.lower().endswith(".json") or name.lower().endswith(".txt")):
                files.append(path)

        files.sort(key=lambda p: os.path.getmtime(p))

        messages = []
        for path in files:
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    raw = f.read()
                try:
                    parsed = json.loads(raw)
                except Exception:
                    parsed = {"raw_text": raw}

                messages.append({
                    "file": os.path.basename(path),
                    "received_utc": datetime.fromtimestamp(os.path.getmtime(path), timezone.utc).isoformat(),
                    "content": parsed
                })

                if archive:
                    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                    dst = os.path.join(archive_dir, stamp + "_" + os.path.basename(path))
                    shutil.move(path, dst)

            except Exception as e:
                messages.append({
                    "file": os.path.basename(path),
                    "error": str(e)
                })

        if messages:
            latest = messages[-1]["content"]
            if isinstance(latest, dict):
                question = latest.get("question") or latest.get("message") or latest.get("raw_text") or str(latest)
            else:
                question = str(latest)

            self._emit_axis_voice(
                message="Inbox read complete. Received bounded user inquiry: " + str(question)[:500],
                message_type="inbox_read",
                priority="normal",
                evidence=[
                    f"messages_read={len(messages)}",
                    "manual_read",
                    "no_cycle",
                    "no_governance_mutation"
                ],
                requires_response=True
            )
        else:
            self._emit_axis_voice(
                message="Inbox read complete. No pending user messages found.",
                message_type="inbox_empty",
                priority="normal",
                evidence=["manual_read", "no_cycle", "no_governance_mutation"],
                requires_response=False
            )

        return messages

'''

with open(ENGINE, "r", encoding="utf-8") as f:
    src = f.read()

if "def _read_axis_inbox" not in src:
    marker = "    def _emit_axis_voice"
    if marker not in src:
        raise RuntimeError("_emit_axis_voice not found. Install voice method first.")
    src = src.replace(marker, method + marker, 1)
    with open(ENGINE, "w", encoding="utf-8") as f:
        f.write(src)
    print("Inserted _read_axis_inbox.")
else:
    print("_read_axis_inbox already present.")

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
    "reason": "installed_manual_axis_inbox_reader_no_cycle",
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
