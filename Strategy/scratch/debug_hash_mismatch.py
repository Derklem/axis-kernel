import json
import hashlib

# Replicate _hash_obj from axis_crypto_helpers
def _canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _hash_obj(obj, domain):
    prefix = f"AXIS::{domain}::".encode("utf-8")
    content = _canonical_json(obj).encode("utf-8")
    return hashlib.sha256(prefix + content).hexdigest()

# Line 34 from the ledger
line_34_json = '{"ts_utc": "2026-05-11T21:36:11.103511+00:00", "cycle": 8, "event_type": "cycle_verdict", "layer": "strategy_engine", "authority_state": "valid", "reason": "cycle_resolved", "ancestry": {"archival_hash": "none", "continuity_cycle": 8}, "prev_witness_hash": "1d429beb284f29a0548ae1e03c5bab38c7cfdc291ded0a59a51dd3758c6667d7", "input_hash": "771f83dc1232d158106b1666084df03c231786831b52a0699a91b99337a0e881", "data": {"frozen": false, "recovery_authorized": false, "rotation_authorized": false, "proposal_phase_complete": true, "causal_links": [], "final_calibration_hash": "d4c55041b7a7bb5ba47015ed70548460634d639662d0a96af32ba37d5c1f0b11", "anchor_hash": "4570684f23e139118e4bfa3a130ad1eea609a8952c186cfe43d7d9f628392d7a", "cycle_start_witness_hash": "651f22508599f0940cfa5c671a3d3709f52a30115c0dcd6ad237431a9a87447f"}, "witness_hash": "efc22091cb7f56aa65c002472789ee3004a95432565711b5d1e3b1a59595fc61"}'

record = json.loads(line_34_json)
stored_hash = record.pop("witness_hash")

computed_hash = _hash_obj(record, "witness_record")

print(f"Stored:   {stored_hash}")
print(f"Computed: {computed_hash}")

if stored_hash == computed_hash:
    print("SUCCESS: Hashes match!")
else:
    print("FAILURE: Hashes do NOT match!")
