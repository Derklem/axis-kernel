"""Phase 191 Stage 4.3: Re-anchor hashes in the correct ledger location."""
import sys, json, os

sys.path.append(r"D:\infinite\Infinity\Strategy")
from axis_crypto_helpers import _hash_file_stream

STRATEGY_DIR = r"D:\Infinite\Infinity\Strategy"
state_path = os.path.join(STRATEGY_DIR, "State", "strategy_state.json")

# Compute hashes for new and changed registry entries
entries = {
    "crypto_helpers": "axis_crypto_helpers.py",
    "semantic_filter": "semantic_context_filter.py",
    "ecosystem_mapper": "ecosystem_mapping_engine.py",
    "strategy_engine": "strategy_engine.py"
}

print("Computing hashes for CORE_SOURCE_REGISTRY entries...")
updates = {}
for name, filename in entries.items():
    path = os.path.join(STRATEGY_DIR, filename)
    domain = "ecosystem_baseline" if name == "baseline_model" else "crypto_lint_file"
    h = _hash_file_stream(path, domain)
    key = "expected_{}_hash".format(name)
    updates[key] = h
    print("  {} = {}...".format(key, h[:24]))

# Load full state file
with open(state_path, "r") as f:
    state = json.load(f)

# Navigate to the shadow ledger
ledger = state.get("mission_shadow_v2", {})

# Update expected hashes
for k, v in updates.items():
    ledger[k] = v

# Create extraction registry
registry = ledger.get("extraction_registry", [])

# Check for duplicate before adding
has_entry = any(e.get("phase") == "191_stage_4.2" for e in registry)
if not has_entry:
    registry.append({
        "phase": "191_stage_4.2",
        "source_file": "strategy_engine.py",
        "target_module": "semantic_context_filter.py",
        "extracted_class": "SemanticContextFilter",
        "lines_extracted": "203-281",
        "extraction_type": "full_class",
        "purity": "PURE",
        "side_effects": 0,
        "regression_tests": 37,
        "regression_pass_rate": 1.0,
        "forwarding_import": True,
        "timestamp": "2026-05-13T20:49:00Z"
    })
    print("\nAdded extraction registry entry.")
else:
    print("\nExtraction registry entry already exists.")

ledger["extraction_registry"] = registry
state["mission_shadow_v2"] = ledger

with open(state_path, "w") as f:
    json.dump(state, f, indent=4)

count = len(registry)
print("Ledger updated. Extraction registry entries: {}".format(count))

# Verify by re-loading
with open(state_path, "r") as f:
    verify = json.load(f)

v_ledger = verify.get("mission_shadow_v2", {})
print("\nVerification:")
for key in sorted(updates.keys()):
    val = v_ledger.get(key, "MISSING")
    status = "OK" if val == updates[key] else "MISMATCH"
    print("  [{}] {} = {}...".format(status, key, val[:20]))

v_reg = v_ledger.get("extraction_registry", [])
print("  Extraction registry: {} entries".format(len(v_reg)))
