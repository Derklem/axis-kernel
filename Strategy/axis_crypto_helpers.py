import json
import hashlib
import os

# Phase 171.3: Unified Cryptographic Authority
HASH_DOMAINS = {
    "witness_record",
    "witness_input",
    "trust_policy",
    "calibration_state",
    "recovery_commitment",
    "evaluation_provenance",
    "observation_evidence",
    "proposal_definition",
    "semantic_edge_state",
    "objective_policy_file",
    "archive_zip",
    "metabolic_target_file",
    "artifact_content_file",
    "crypto_lint_file",
    "governance_capsule",
    "metabolic_receipt_snapshot",
    "witness_ledger_snapshot",
    "ecosystem_receipt",
    "ecosystem_receipt_chain",
    "ecosystem_baseline",
    "metabolic_receipt_chain",
    "epistemic_claim",
    "epistemic_dispute",
    "epistemic_source",
    "epistemic_candidate",
    "processed_observation",
    "ontology_seal",
    "node_attestation",
    "refactor_target",
    "refactor_proposal"
}

def _canonical_json(obj):
    """Phase 73/74: Deterministic JSON serialization for canonical hashing."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _hash_obj(obj, domain):
    """Phase 73/74/75/77/171.3: Deterministic hash with strict domain separation."""
    if domain not in HASH_DOMAINS: raise ValueError(f"Unauthorized hash domain: {domain}")
    prefix = f"AXIS::{domain}::".encode("utf-8")
    content = _canonical_json(obj).encode("utf-8")
    return hashlib.sha256(prefix + content).hexdigest()

def _hash_bytes(data: bytes, domain):
    """Phase 76/77/171.3: Raw byte hash with strict domain separation."""
    if domain not in HASH_DOMAINS: raise ValueError(f"Unauthorized hash domain: {domain}")
    prefix = f"AXIS::{domain}::".encode("utf-8")
    return hashlib.sha256(prefix + data).hexdigest()

def _hash_file_stream(path, domain, chunk_size=65536):
    """Phase 77/171.3: Streaming file hash with strict domain separation."""
    if domain not in HASH_DOMAINS: raise ValueError(f"Unauthorized hash domain: {domain}")
    sha = hashlib.sha256(f"AXIS::{domain}::".encode("utf-8"))
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha.update(chunk)
    return sha.hexdigest()

def _gen_convenience_id(data: str):
    """Phase 171.2: Non-authoritative ID generation for filenames/short IDs."""
    return hashlib.sha256(data.encode()).hexdigest()[:8]
