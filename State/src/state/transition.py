import json
import copy
from importlib.resources import files
from jsonschema import validate
from referencing import Registry, Resource
from jsonschema import Draft7Validator
from laboratory.crypto import canonical_hash
from state import TRANSITION_ENGINE_VERSION

SAFE_INTEGER_MAX = 9007199254740991

def load_schema(package, name):
    # Load schema from package data
    schema_text = files(f"{package}.schemas").joinpath(name).read_text(encoding="utf-8")
    return json.loads(schema_text)

def transition(prior_state: dict, observation_feed: dict, transition_spec: dict) -> dict:
    state_vector_schema = load_schema("state", "state_vector.json")
    validate(instance=prior_state, schema=state_vector_schema)
    validate(instance=observation_feed, schema=load_schema("observation", "observation_feed.json"))
    validate(instance=transition_spec, schema=load_schema("state", "transition_spec.json"))

    prior_state_root = canonical_hash(prior_state)
    observation_feed_root = canonical_hash(observation_feed)
    transition_spec_root = canonical_hash(transition_spec)

    reason_codes = set()
    summary = {
        "supported_applied": 0,
        "inconclusive_applied": 0,
        "contradicted_applied": 0,
        "replayed_skipped": 0,
        "subject_mismatch_skipped": 0
    }

    # Extract already applied IDs
    previously_applied = set(prior_state.get("applied_observation_ids", []))
    
    # Track duplicates within this feed
    feed_seen = set()
    
    new_applied = []
    skipped = []
    
    # 12. Never mutate input (use a copy for evidence count)
    evidence_count = prior_state["evidence_count"]
    
    for obs in observation_feed.get("observations", []):
        obs_id = obs["observation_id"]
        
        # 3. Reject duplicate IDs within the observation feed.
        if obs_id in feed_seen:
            raise ValueError(f"Duplicate observation ID in feed: {obs_id}")
        feed_seen.add(obs_id)
        
        # 4. Select observations matching transition_spec.subject.
        if obs["subject"] != transition_spec["subject"]:
            summary["subject_mismatch_skipped"] += 1
            reason_codes.add("SUBJECT_MISMATCH_SKIPPED")
            skipped.append(obs_id)
            continue
            
        # 5. Skip observations already recorded in prior_state.applied_observation_ids.
        if obs_id in previously_applied:
            summary["replayed_skipped"] += 1
            reason_codes.add("REPLAYED_OBSERVATION_SKIPPED")
            skipped.append(obs_id)
            continue
            
        new_applied.append(obs_id)
        
        support = obs["support"]
        if support == 1:
            # 6. For support = 1: add supported_increment
            evidence_count += transition_spec["supported_increment"]
            summary["supported_applied"] += 1
            reason_codes.add("SUPPORTED_OBSERVATION_APPLIED")
        elif support == 0:
            # 7. For support = 0: no change to evidence_count
            summary["inconclusive_applied"] += 1
            reason_codes.add("INCONCLUSIVE_OBSERVATION_APPLIED")
        elif support == -1:
            # 8. For support = -1: emit CONTRADICTION_OBSERVED
            summary["contradicted_applied"] += 1
            reason_codes.add("CONTRADICTION_OBSERVED")

    # 9. Clamp evidence_count at the canonical safe-integer maximum
    if evidence_count > SAFE_INTEGER_MAX:
        evidence_count = SAFE_INTEGER_MAX
        reason_codes.add("EVIDENCE_COUNT_CLAMPED")

    # 10. Sort applied_observation_ids lexically
    final_applied = sorted(list(previously_applied) + new_applied)
    skipped = sorted(skipped)
    new_applied = sorted(new_applied)

    # 11. Sort all collected reason_codes lexically
    if not reason_codes and not new_applied:
        reason_codes.add("NO_STATE_CHANGE")

    sorted_reason_codes = sorted(list(reason_codes))

    next_state = {
        "state_schema_version": "1.1.0",
        "confidence": prior_state["confidence"],
        "evidence_count": evidence_count,
        "applied_observation_ids": final_applied
    }
    
    next_state_root = canonical_hash(next_state)

    transition_artifact = {
        "state_transition_schema_version": "1.0.0",
        "transition_version": transition_spec["transition_version"],
        "transition_engine_version": TRANSITION_ENGINE_VERSION,
        "prior_state_root": prior_state_root,
        "observation_feed_root": observation_feed_root,
        "transition_spec_root": transition_spec_root,
        "next_state_root": next_state_root,
        "next_state": next_state,
        "applied_observation_ids": new_applied,
        "skipped_observation_ids": skipped,
        "summary": summary,
        "reason_codes": sorted_reason_codes
    }
    
    transition_schema = load_schema("state", "state_transition.json")
    registry = Registry().with_resource(
        "urn:axis:state-vector:1.1.0",
        Resource.from_contents(state_vector_schema),
    )
    validator = Draft7Validator(transition_schema, registry=registry)
    validator.validate(transition_artifact)

    return transition_artifact
