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
backup_dir = os.path.join(COMM, "ARCHIVE", "pre_axis_voice_method_" + stamp)
os.makedirs(backup_dir, exist_ok=True)
shutil.copy2(ENGINE, os.path.join(backup_dir, "strategy_engine.py"))

method = r'''
    def _emit_axis_voice(self, message: str, message_type="status", priority="normal",
                        evidence=None, requires_response=False):
        """Simple Voice Layer - Direct channel for Axis to speak to user."""
        voice_path = r"D:\Infinite\Infinity\Runtime\Decision\axis_voice.json"

        entry = {
            "timestamp_utc": self._now(),
            "speaker": "AXIS",
            "message_type": message_type,
            "priority": priority,
            "epoch": self.shadow_ledger.get("cycle_count", 0),
            "message": str(message),
            "evidence": evidence or [],
            "requires_response": requires_response,
            "last_updated_cycle": self.shadow_ledger.get("cycle_count", 0)
        }

        try:
            tmp_path = voice_path + ".tmp"
            import json, os
            os.makedirs(os.path.dirname(voice_path), exist_ok=True)
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(entry, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, voice_path)

            print(f"AXIS VOICE -> {message_type.upper()}: {message[:120]}...")
        except Exception as e:
            print(f"DEBUG: Failed to emit axis voice: {e}")

'''

with open(ENGINE, "r", encoding="utf-8") as f:
    src = f.read()

if "def _emit_axis_voice" not in src:
    marker = "    def _dry_run_extraction"
    if marker not in src:
        marker = "    def _observe_own_codebase"
    if marker not in src:
        raise RuntimeError("Could not find safe insertion marker.")
    src = src.replace(marker, method + marker, 1)
    with open(ENGINE, "w", encoding="utf-8") as f:
        f.write(src)
    print("Inserted _emit_axis_voice.")
else:
    print("_emit_axis_voice already present.")

# Syntax check
import py_compile
py_compile.compile(ENGINE, doraise=True)
print("py_compile OK.")

# Update expected strategy_engine hash + calibration hash
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
    "reason": "installed_manual_axis_voice_method_no_cycle",
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
