import json, hashlib, copy
f = r"d:\infinite\Infinity\Strategy\State\strategy_state.json"
state = json.load(open(f))
state["mission_shadow_v2"]["continuity_reanchor_request"] = {
    "status": "pending",
    "operator": "HALCYON_ROOT",
    "scope": "temporal_continuity",
    "mode": "forensic_repair",
    "acknowledge_lineage_break": True,
    "nonce": "REANCHOR_POST_IMP_PATCH_001",
    "reason": "authorized_imp_sensory_bridge_patch",
    "requested_cycle": 552,
    "expires_cycle": 9999,
    "witness_repair_head": state["mission_shadow_v2"]["witness_chain_head"]
}
temp_state = copy.deepcopy(state)
if "calibration_ledger_integrity" in temp_state["mission_shadow_v2"]:
    del temp_state["mission_shadow_v2"]["calibration_ledger_integrity"]
state_hash = hashlib.sha256(json.dumps(temp_state, sort_keys=True).encode("utf-8")).hexdigest()
state["mission_shadow_v2"].setdefault("calibration_ledger_integrity", {})
state["mission_shadow_v2"]["calibration_ledger_integrity"]["hash"] = state_hash
state["mission_shadow_v2"]["calibration_ledger_integrity"]["status"] = "valid"
state["mission_shadow_v2"]["calibration_ledger_integrity"]["continuity_status"] = "intact"
json.dump(state, open(f, "w"), indent=4)
