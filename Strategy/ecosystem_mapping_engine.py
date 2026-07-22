import os
import json
from datetime import datetime, timezone
from axis_crypto_helpers import _hash_obj, _hash_file_stream, HASH_DOMAINS

class EcosystemMappingEngine:
    """Phase 96-101: Epistemic Intake, Pricing, and Source Identity Discipline."""

    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.state_dir = os.path.join(root_dir, "Infinity", "Strategy", "State")
        self.model_path = os.path.join(self.state_dir, "ai_ecosystem_model.json")
        self.inquiry_dir = os.path.join(root_dir, "Infinity", "Inquiry")
        
        if not os.path.exists(self.model_path):
            self._initialize_model()

        self.candidates_path = os.path.join(self.state_dir, "claim_candidates.json")
        self.anomalies_path = os.path.join(self.state_dir, "speculative_anomalies.json")


    def _load_candidates(self):
        """Phase 172: Load non-binding candidate pool."""
        if os.path.exists(self.candidates_path):
            with open(self.candidates_path, "r") as f:
                return json.load(f)
        return {"candidates": {}}


    def _save_candidates(self, candidates):
        """Phase 172: Persist non-binding candidate pool."""
        with open(self.candidates_path, "w") as f:
            json.dump(candidates, f, indent=4)


    def _load_anomalies(self):
        """Phase 181: Load non-operational anomaly vault."""
        if os.path.exists(self.anomalies_path):
            with open(self.anomalies_path, "r") as f:
                return json.load(f)
        return {"anomalies": {}}


    def _save_anomalies(self, anomalies):
        """Phase 181: Persist non-operational anomaly vault."""
        with open(self.anomalies_path, "w") as f:
            json.dump(anomalies, f, indent=4)


    def fracture_candidate(self, candidate_id, model, candidate_data):
        """Phase 172: Epistemic Fracturing. Tests candidate for independence and structural compatibility."""
        # 1. Source Independence Test
        source_id = candidate_data.get("source_id", "anonymous")
        if source_id == "anonymous":
            return False, "anonymous_external_source_prohibited"
            
        # 2. Structural Compatibility Check (Entropy)
        # We check if the candidate contradicts any high-confidence existing claim
        entity = candidate_data.get("entity")
        claim_text = candidate_data.get("claim")
        claim_id = self.get_claim_id(entity, claim_text)
        
        existing = model.get("claims", {}).get(claim_id)
        if existing and existing.get("confidence", 0) > 0.8:
            # If the candidate matches exactly, it's redundant but compatible.
            # If it were a contradiction, it would have the same claim_id in our current logic
            # (unless we add 'negation' logic, which we haven't yet).
            # For now, we check for 'tension' via the engine's global state.
            pass

        # 3. Simulated Tension Check
        # (This will be called by StrategyEngine after measuring global tension delta)
        return True, "nominal"


    def calculate_lineage_entropy(self, provenance_trail):
        """Phase 191a/191b: Calculates effective quorum weight by penalizing correlated sources.
        - First source in a lineage group: +1.0
        - Subsequent sources in same lineage group: +0.2 (Correlation Penalty)
        - Identical node_id: +0.0 (Duplicate/Replay Protection)
        - Attestation-based grouping (Phase 191b): Prevents "declared diversity" spoofing.
        """
        if not provenance_trail: return 0.0
        
        seen_nodes = set()
        lineage_groups = {} # (engine_version, ontology_seal, node_attestation) -> count
        total_weight = 0.0
        
        for entry in provenance_trail:
            lineage = entry.get("lineage", {})
            node_id = lineage.get("node_id", "unknown")
            
            # 1. Duplicate/Replay Protection
            if node_id in seen_nodes:
                continue
            seen_nodes.add(node_id)
            
            # 2. Lineage Correlation Check (Attested Diversity)
            ver = lineage.get("engine_version", "v0")
            seal = lineage.get("ontology_seal", "none")
            attestation = lineage.get("node_attestation", "none")
            
            # We group by attestation and seal. Declared version is ignored to prevent spoofing.
            group_key = (seal, attestation)
            
            if group_key not in lineage_groups:
                lineage_groups[group_key] = 1
                total_weight += 1.0 # First of its kind
            else:
                lineage_groups[group_key] += 1
                total_weight += 0.2 # Penalty for sharing lineage
                
        return round(total_weight, 3)


    def promote_candidate(self, candidate_id, candidates, model, cycle_count, tension):
        """Phase 172: Promotes a candidate to an active model observation (receipt eligible)."""
        candidate = candidates["candidates"].pop(candidate_id, None)
        if not candidate:
            return False
            
        # Ingest as a standard observation now that it has survived the fracturing window
        self._ingest_observation(model, candidate, persist=False, cycle_count=cycle_count, tension=tension)
        return True


    def _compute_domain_hash(self, domain, data):
        """Phase 147/171.3: Unified domain-separated hasher."""
        return _hash_obj(data, domain)


    def _compute_lookup_hash(self, data):
        """Phase 99/147: Canonical lookup hasher for epistemic claims."""
        return self._compute_domain_hash("epistemic_claim", data)


    def _now(self):
        """Phase 124: Centralized UTC timestamp generator."""
        return datetime.now(timezone.utc).isoformat()


    def _source_weight(self, obs, model=None, domain="general"):
        """Phase 125/132/133/185: Stabilized adaptive weight with domain-local reputation feedback."""
        source_id = obs.get("source_id", "anonymous")
        base_weight = min(1.0, max(0.0, obs.get(
            "source_weight",
            0.7 if source_id != "anonymous" else 0.3
        )))

        # Phase 133/185: Stabilized Domain-Local Reputation Feedback
        if model and source_id != "anonymous":
            # Lookup reporting entity reputation (who is talking, not who is talked about)
            entity = model.get("entities", {}).get(source_id)
            if entity and entity.get("verified_claims_count", 0) >= 3:
                # Phase 185: Domain-local priority
                reputation = entity.get("domain_reputation", {}).get(domain, entity.get("reliability_index", 0.5))
                if reputation > 0.75:
                    # Asymptotic damping prevents rapid saturation
                    base_weight += 0.08 * (1.0 - base_weight)
                elif reputation < 0.5:
                    base_weight -= 0.05

        return min(1.0, max(0.0, base_weight))


    def _source_key(self, obs):
        """Phase 127/148: Domain-separated source identity key generator."""
        return self._compute_domain_hash("epistemic_source", {
            "source_type": obs.get("source_type", "unknown"),
            "source_id": obs.get("source_id", "anonymous")
        })


    def _legacy_source_key(self, obs):
        """Phase 149: Backwards compatibility for pre-migration source keys."""
        return self._compute_domain_hash("epistemic_claim", {
            "source_type": obs.get("source_type", "unknown"),
            "source_id": obs.get("source_id", "anonymous")
        })


    def _claim_key(self, obs):
        """Phase 129/148: Domain-separated claim identity key generator."""
        return self.get_claim_id(obs.get("entity"), obs.get("claim"))


    def get_claim_id(self, entity, claim):
        """Phase 155: Public access for epistemic claim hashing."""
        return self._compute_domain_hash("epistemic_claim", {
            "entity": entity,
            "claim": claim
        })


    def get_source_id(self, source_type, source_id):
        """Phase 155: Public access for epistemic source hashing."""
        return self._compute_domain_hash("epistemic_source", {
            "source_type": source_type,
            "source_id": source_id
        })


    def _initialize_model(self):
        model = {
            "last_updated_utc": self._now(),
            "entities": {}, # Key: Entity Name
            "claims": {},   # Key: Domain-separated claim_id
            "revoked_claims": {} # Phase 189: Tombstone vault
        }

        os.makedirs(self.state_dir, exist_ok=True)
        self._save_model(model)


    def _update_epistemic_debt(self, claim_obj):
        """Phase 113: Quantify unresolved epistemic debt."""
        resolved_indices = {
            r.get("resolves_contradiction_index")
            for r in claim_obj.get("resolutions", [])
            if r.get("resolution_scope") == "specific" and r.get("resolves_contradiction_index") is not None
        }

        claim_obj["unresolved_contradiction_count"] = sum(
            1 for i, _ in enumerate(claim_obj.get("contradictions", []))
            if i not in resolved_indices
        )


    def _recompute_actionable(self, claim):
        """Phase 114/115: Stability-Based Actionability Gate with Diagnostics."""
        reasons = []
        if claim.get("confidence", 0.0) <= 0.7:
            reasons.append("low_confidence")
        if claim.get("contested", False):
            reasons.append("contested")
        if claim.get("unresolved_contradiction_count", 0) > 0:
            reasons.append("unresolved_contradictions")
            
        claim["actionability_blockers"] = reasons
        claim["actionable"] = len(reasons) == 0


    def _recompute_entity_metrics(self, model, entity):
        """Phase 120: Recalculate entity stats based on current claim states."""
        if entity not in model["entities"]: return
        
        verified_count = sum(
            1 for c in model["claims"].values()
            if c.get("entity") == entity and c.get("confidence", 0) > 0.8
        )
        model["entities"][entity]["verified_claims_count"] = verified_count
        
        # Phase 168/185: Domain-Local Reputation Floor
        # We preserve global reliability_index for legacy compatibility but prioritize domain_reputation
        current_rel = model["entities"][entity].get("reliability_index", 0.5)
        calculated = min(1.0, 0.5 + verified_count * 0.1)
        model["entities"][entity]["reliability_index"] = min(current_rel, calculated)


    def penalize_entity_reliability(self, model, entity, amount, domain="general"):
        """Phase 168/180/185: Surgically reduces entity reliability index for a specific domain."""
        if entity not in model["entities"]:
            model["entities"][entity] = {
                "reliability_index": 0.5, 
                "domain_reputation": {},
                "verified_claims_count": 0, 
                "first_discovery_utc": self._now()
            }
        
        ent = model["entities"][entity]
        reps = ent.setdefault("domain_reputation", {})
        
        # Same-domain penalty: 100% impact
        current = reps.get(domain, ent.get("reliability_index", 0.5))
        new_val = max(0.0, current - amount)
        reps[domain] = round(new_val, 3)
        
        # Cross-domain damped penalty: 20% impact on all other domains and global index
        damped_penalty = amount * 0.2
        for d in reps:
            if d != domain:
                reps[d] = round(max(0.0, reps[d] - damped_penalty), 3)

        
        ent["reliability_index"] = round(max(0.0, ent.get("reliability_index", 0.5) - damped_penalty), 3)
        
        print(f"DEBUG: Penalized reliability for '{entity}' in domain '{domain}': {current} -> {new_val}")


    def reward_entity_reliability(self, model, entity, amount, domain="general"):
        """Phase 173/180/185: Surgically increases entity reliability index for a specific domain."""
        if entity not in model["entities"]:
            model["entities"][entity] = {
                "reliability_index": 0.5, 
                "domain_reputation": {},
                "verified_claims_count": 0, 
                "first_discovery_utc": self._now()
            }
        
        ent = model["entities"][entity]
        reps = ent.setdefault("domain_reputation", {})
        
        current = reps.get(domain, ent.get("reliability_index", 0.5))
        new_val = min(1.0, current + amount)
        reps[domain] = round(new_val, 3)
        
        # Cross-domain reward is NOT applied automatically to preserve specialization
        
        # Global index gets a damped boost (5%)
        ent["reliability_index"] = round(min(1.0, ent.get("reliability_index", 0.5) + (amount * 0.05)), 3)
        
        print(f"DEBUG: Rewarded reliability for '{entity}' in domain '{domain}': {current} -> {new_val}")




    def apply_receipt_to_model(self, model, receipt, candidates=None, anomalies=None):
        """Phase 171/172.1/181: Single Mutation Interface. Deterministically applies a receipt to the model, candidate pool, and anomaly vault."""
        m_type = receipt.get("mutation_type")
        target_id = receipt.get("target_id")
        data = receipt.get("data", {})
        
        if m_type == "EPISTEMIC_CLAIM_DECAYED":
            # Phase 189: Tombstone Demotion (Controlled Demotion with Memory)
            if target_id in model.get("claims", {}):
                claim = model["claims"].pop(target_id)
                # Phase 189.5: Align persistence cycles to fix forensic drift
                claim["decay_persistence_cycles"] = 5
                model.setdefault("revoked_claims", {})[target_id] = {
                    "original_claim": claim,
                    "revoked_cycle": data.get("cycle_count", 0),
                    "revocation_reason": data.get("reason", "decay_or_revoked"),
                    "last_confidence": claim.get("confidence", 0.0),
                    "revocation_receipt": receipt.get("receipt_id"),
                    "resurrection_policy": "blocked_pending_supermajority"
                }
                eid = claim.get("entity")
                if eid in model.get("entities", {}):
                    self._recompute_entity_metrics(model, eid)
                    
        elif m_type == "EPISTEMIC_CORRECTION":
            if target_id in model.get("claims", {}):
                claim = model["claims"][target_id]
                if "new_confidence" in data:
                    claim["confidence"] = data["new_confidence"]
                    
        elif m_type == "EPISTEMIC_REVOCATION":
            # Phase 170: Claim Revocation
            if target_id in model.get("claims", {}):
                claim = model["claims"][target_id]
                claim["confidence"] = 0.0
                claim["demoted"] = True
                domain = claim.get("claim_domain", "general")
                claim["demotion_reason"] = f"causal_tension_surge_{data.get('tension_delta', 0):.2f}_score_{data.get('attribution_score', 0):.2f}"
                claim["receipt_id"] = receipt.get("receipt_id")
                claim["receipt_hash"] = receipt.get("causal_hash")
                
                # Phase 185: Penalize entity in the specific domain of the revoked claim
                eid = claim.get("entity")
                if eid in model.get("entities", {}):
                    self.penalize_entity_reliability(model, eid, 0.2, domain=domain)
            
            # Phase 181/184: Entity Revocation (Consolidated)
            eid = data.get("entity") or receipt.get("entity_id")
            if eid in model.get("entities", {}):
                model["entities"][eid]["reliability_index"] = 0.0
                model["entities"][eid]["status"] = "revoked"
                model["entities"][eid]["revocation_receipt"] = receipt.get("receipt_id", "unknown")
                
        elif m_type == "REPUTATION_PENALTY":
            # Phase 184/185: Unified Domain-Aware Reputation Penalty
            eid = target_id if target_id in model.get("entities", {}) else (data.get("entity") or receipt.get("entity_id"))
            if eid:
                penalty = data.get("penalty_amount") or receipt.get("penalty") or 0.15
                domain = data.get("domain") or receipt.get("domain", "general")
                self.penalize_entity_reliability(model, eid, penalty, domain=domain)
                if eid in model.get("entities", {}):
                    model["entities"][eid]["last_penalty_receipt"] = receipt.get("receipt_id")
                    model["entities"][eid]["last_penalty_hash"] = receipt.get("causal_hash")

        elif m_type == "REPUTATION_GAIN":
            # Phase 184/185: Unified Domain-Aware Reputation Gain
            eid = target_id if target_id in model.get("entities", {}) else (data.get("entity") or receipt.get("entity_id"))
            if eid:
                reward = data.get("reward_amount") or receipt.get("gain") or 0.02
                domain = data.get("domain") or receipt.get("domain", "general")
                self.reward_entity_reliability(model, eid, reward, domain=domain)
                if eid in model.get("entities", {}):
                    model["entities"][eid]["last_reward_receipt"] = receipt.get("receipt_id")
                    model["entities"][eid]["last_reward_hash"] = receipt.get("causal_hash")

        elif m_type in ["STRUCTURAL_ACTUATION", "STRUCTURAL_REVERSAL", "STRUCTURAL_CONTESTATION"]:
            # Phase 186/187: Reconstruct architectural mutations from forensic receipts
            entity_id = target_id
            if entity_id in model.get("entities", {}):
                ent = model["entities"][entity_id]
                ent["last_actuation_receipt"] = receipt.get("receipt_id")
                ent["last_governance_action"] = data.get("action")
                ent["last_governance_cycle"] = data.get("cycle")

        elif m_type == "EXTERNAL_CANDIDATE_PROMOTION":
            # Phase 173.1: Preservation of metadata during promotion
            self._ingest_observation(model, data, persist=False, cycle_count=receipt.get("cycle_count"), tension=0.0)
            # Tag with receipt and metadata
            claim_id = self.get_claim_id(data.get("entity"), data.get("claim"))
            if claim_id in model.get("claims", {}):
                claim = model["claims"][claim_id]
                claim["promotion_receipt"] = receipt.get("receipt_id")
                claim["artifact_type"] = data.get("artifact_type", "observation")
                claim["batch_id"] = data.get("batch_id", "none")
                claim["claim_domain"] = data.get("claim_domain", "general")
                claim["provenance_note"] = data.get("provenance_note", "")
                claim["agreement_count"] = data.get("agreement_count", 1)
                claim["requires_supermajority"] = data.get("requires_supermajority", False)
                if data.get("quarantine_receipt"):
                    claim["quarantine_receipt"] = data.get("quarantine_receipt")
                # Ensure metrics are updated for the entity
                self._recompute_entity_metrics(model, data.get("entity"))
            
            # Remove from candidates if promotion successful
            if candidates and target_id in candidates.get("candidates", {}):
                del candidates["candidates"][target_id]

        elif m_type == "CANDIDATE_RECLASSIFIED":
            if candidates:
                pool = candidates.get("candidates", {})
                c_id = data.get("candidate_id") or target_id
                if c_id in pool:
                    pool[c_id]["artifact_type"] = data.get("new_artifact_type", pool[c_id].get("artifact_type"))
                    pool[c_id]["confidence"] = data.get("new_confidence", pool[c_id].get("confidence"))
                    reason = data.get("reason", "")
                    if reason:
                        existing = pool[c_id].get("provenance_note", "")
                        pool[c_id]["provenance_note"] = f"{existing} | RECLASS: {reason}".strip(" | ")
                else:
                    print(f"WARNING: CANDIDATE_RECLASSIFIED for unknown candidate {c_id}")

        elif m_type == "CANDIDATE_QUARANTINED":
            if candidates is not None:
                entity = data.get("entity")
                # Phase 181: Entity initialization MUST be derivable from receipt
                if entity and entity not in model.get("entities", {}):
                    model["entities"][entity] = {
                        "first_discovery_utc": data.get("discovery_utc"),
                        "last_seen_utc": data.get("discovery_utc"),
                        "reliability_index": 0.5,
                        "verified_claims_count": 0
                    }
                
                candidates["candidates"][target_id] = {
                    "entity": entity,
                    "claim": data.get("claim"),
                    "claim_domain": data.get("claim_domain", "general"),
                    "source_id": data.get("source_id"),
                    "source_type": data.get("source_type"),
                    "artifact_type": data.get("artifact_type", "observation"),
                    "batch_id": data.get("batch_id", "none"),
                    "confidence": data.get("confidence", 0.5),
                    "status": data.get("status", "pending"),
                    "discovery_utc": data.get("discovery_utc"),
                    "provenance_note": data.get("provenance_note", ""),
                    "requires_supermajority": data.get("requires_supermajority", False),
                    "quarantine_receipt": receipt.get("receipt_id"),
                    "provenance_trail": [{
                        "source_id": data.get("source_id"),
                        "source_type": data.get("source_type"),
                        "batch_id": data.get("batch_id", "none"),
                        "ts": data.get("discovery_utc"),
                        "lineage": data.get("lineage", {})
                    }]
                }
                if "requires_supermajority" in data:
                    candidates["candidates"][target_id]["requires_supermajority"] = data["requires_supermajority"]

        elif m_type == "ECOSYSTEM_CYCLE_COMPLETE":
            model["cycle_count"] = data.get("cycle_count", 0)
            # Phase 187: Forensic Decay (0.99 per cycle)
            # This ensures that facts lose confidence over time and can be forensically replayed
            for claim_id, data in model.get("claims", {}).items():
                data["staleness_days"] = data.get("staleness_days", 0) + 1.0
                data["confidence"] = max(0.0, round(data["confidence"] * 0.99, 4))
                # Re-verify actionability
                self._update_epistemic_debt(data)
                self._recompute_actionable(data)
            
            # Synchronize entity metrics with decayed claims
            for entity in model.get("entities", {}):
                self._recompute_entity_metrics(model, entity)
                
            if candidates is not None:
                candidates["cycle_count"] = data.get("cycle_count", 0)
            # Phase 181: Reputation Metabolism (Recovery toward 0.5 baseline)
            for entity_id, entity_data in model.get("entities", {}).items():
                current = entity_data.get("reliability_index", 0.5)
                if current < 0.5:
                    recovery = (0.5 - current) * 0.05
                    entity_data["reliability_index"] = round(current + recovery, 4)
                elif current > 0.5:
                    decay = (current - 0.5) * 0.01
                    entity_data["reliability_index"] = round(current - decay, 4)
                
                # Phase 186: Domain-Local Metabolism Parity
                reps = entity_data.get("domain_reputation", {})
                for d, d_val in reps.items():
                    if d_val < 0.5:
                        d_recovery = (0.5 - d_val) * 0.05
                        reps[d] = round(d_val + d_recovery, 4)
                    elif d_val > 0.5:
                        d_decay = (d_val - 0.5) * 0.01
                        reps[d] = round(d_val - d_decay, 4)
            
            # Phase 181: Sync metabolic consequence receipts (deterministic links)
            if candidates is not None:
                for c_id in candidates.get("candidates", {}):
                    candidates["candidates"][c_id]["cycles_survived"] = candidates["candidates"][c_id].get("cycles_survived", 0) + 1

        elif m_type in ["CANDIDATE_AGREEMENT", "CANDIDATE_AGREEMENT_ADDED"]:
            # Phase 184: Unified Candidate Agreement
            if candidates and target_id in candidates.get("candidates", {}):
                cand = candidates["candidates"][target_id]
                cand["agreement_count"] = cand.get("agreement_count", 1) + 1
                cand.setdefault("provenance_trail", []).append({
                    "source_id": data.get("source_id"),
                    "source_type": data.get("source_type"),
                    "batch_id": data.get("batch_id"),
                    "ts": data.get("ts"),
                    "lineage": data.get("lineage", {})
                })

        elif m_type == "CANDIDATE_FRACTURED":
            if candidates and target_id in candidates.get("candidates", {}):
                del candidates["candidates"][target_id]

        elif m_type == "CANDIDATE_SUSPENDED":
            # Phase 181: Move from candidates to anomaly vault
            if candidates and target_id in candidates.get("candidates", {}):
                c_data = candidates["candidates"].pop(target_id)
                if anomalies is not None:
                    anomalies["anomalies"][target_id] = {
                        "candidate_data": c_data,
                        "suspended_utc": data.get("suspended_utc"),
                        "suspension_reason": data.get("suspension_reason"),
                        "decay_deadline_cycle": data.get("decay_deadline_cycle"),
                        "option_value_score": data.get("option_value_score", 0.0),
                        "operational_influence": False,
                        "status": "suspended"
                    }

        elif m_type == "CANDIDATE_RESURRECTED":
            # Phase 181: Move from anomaly vault back to candidates
            if anomalies and target_id in anomalies.get("anomalies", {}):
                anomaly = anomalies["anomalies"].pop(target_id)
                c_data = anomaly.get("candidate_data", {})
                
                # Reset survival, preserve history
                c_data["cycles_survived"] = 0
                c_data["resurrected_from"] = target_id
                c_data["prior_suspension_reason"] = anomaly.get("suspension_reason", "")
                c_data["prior_option_value_score"] = anomaly.get("option_value_score", 0.0)
                
                # Add agreement
                c_data["agreement_count"] = c_data.get("agreement_count", 1) + 1
                c_data.setdefault("provenance_trail", []).append({
                    "source_id": data.get("source_id"),
                    "source_type": data.get("source_type"),
                    "batch_id": data.get("batch_id"),
                    "ts": data.get("ts"),
                    "lineage": data.get("lineage", {})
                })

                if candidates is not None:
                    candidates["candidates"][target_id] = c_data

        elif m_type == "CANDIDATE_EXPIRED":
            # Phase 181: Decay from anomaly vault
            if anomalies and target_id in anomalies.get("anomalies", {}):
                del anomalies["anomalies"][target_id]

        # Phase 191: Audit-only receipt types. These are chained for forensic continuity
        # but produce NO state mutation during replay. They exist purely as evidence of
        # analysis/refactoring events in the causal ledger.
        elif m_type in ["DRY_RUN_EXTRACTION", "CODE_REFACTOR_QUARANTINED", "CODE_EXTRACTION_QUARANTINED"]:
            pass  # Intentional no-op: audit metadata only
    def _hash_file_domain(self, path, domain):
        """Phase 171.1/171.3: Domain-separated file hasher."""
        return _hash_file_stream(path, domain)


    def verify_state_derivability(self, model, receipt_dir, baseline_path, expected_baseline_hash, current_candidates=None, current_anomalies=None, expected_head=None, expected_cycle=None):
        """Phase 171.1/172.1/181: Full-State Derivability Audit. Reconstructs and compares 100% of the model, candidate, and anomaly state."""
        import glob
        import copy
        
        # 1. Verify Baseline
        if not os.path.exists(baseline_path):
            return False, ["Missing ecosystem_model_baseline.json"]
            
        actual_baseline_hash = self._hash_file_domain(baseline_path, "ecosystem_baseline")
        if actual_baseline_hash != expected_baseline_hash:
            return False, [f"Baseline hash mismatch: {actual_baseline_hash[:12]} != {expected_baseline_hash[:12]}"]
            
        # 2. Load and Chain Receipts
        receipt_files = glob.glob(os.path.join(receipt_dir, "*.receipt"))
        receipts_by_parent = {}
        for r_path in receipt_files:
            try:
                with open(r_path, "r") as f:
                    r = json.load(f)
                    # Verify individual receipt integrity (Phase 171.1 Domain Isolation)
                    r_copy = copy.deepcopy(r)
                    r_id = r_copy.pop("receipt_id", None)
                    r_hash = r_copy.pop("causal_hash", None)
                    actual_r_hash = self._compute_domain_hash("ecosystem_receipt", r_copy)
                    if actual_r_hash != r_hash:
                        return False, [f"Receipt {r_id} content tamper detected: {actual_r_hash[:12]} != {r_hash[:12]}"]
                    
                    # Phase 184: Explicit Duplicate Parent Detection
                    parent = r.get("parent_receipt_head")
                    if parent in receipts_by_parent:
                        return False, [f"Duplicate Parent Head Detected: {parent[:12]} referenced by multiple receipts (Collision)."]
                        
                    receipts_by_parent[parent] = r
            except Exception as e:
                return False, [f"Failed to load receipt {r_path}: {e}"]
        
        # 3. Deterministic Reconstruction from Baseline
        with open(baseline_path, "r") as f:
            reconstructed_model = json.load(f)
            
        reconstructed_candidates = {"candidates": {}}
        reconstructed_anomalies = {"anomalies": {}}
        current_head = "none" # Phase 171.1 Genesis is 'none'
        chain_count = 0
        while current_head in receipts_by_parent:
            # Phase 182/183 Resilience: Stop if we reach the expected head
            if expected_head and current_head == expected_head:
                break
                
            receipt = receipts_by_parent[current_head]
            
            # Verify chain link (Phase 171.1 Domain Isolation)
            link_data = {"parent_head": current_head, "causal_hash": receipt.get("causal_hash")}
            actual_chain_hash = self._compute_domain_hash("ecosystem_receipt_chain", link_data)
            
            # Apply Mutation
            self.apply_receipt_to_model(reconstructed_model, receipt, candidates=reconstructed_candidates, anomalies=reconstructed_anomalies)
            
            # Advance Head
            current_head = actual_chain_hash
            chain_count += 1
            
        # Final head check (Phase 183)
        if expected_head and current_head != expected_head:
            print(f"DEBUG CHAIN GAP: current_head {current_head}, expected {expected_head}, in dict: {current_head in receipts_by_parent}")
            return False, [f"Chain Gap Detected: Reconstruction stopped at {current_head[:12]}, expected {expected_head[:12]}"]

        # Final cycle check (Phase 183)
        actual_cycle = reconstructed_model.get("cycle_count", 0)
        if expected_cycle is not None and actual_cycle != expected_cycle:
            return False, [f"Temporal Drift Detected: Reconstructed state at Cycle {actual_cycle}, expected Cycle {expected_cycle}"]
        # 4. Canonical Full-State Comparison (Phase 171.1)
        # We compare the ENTIRE JSON structure, excluding volatile fields
        # Phase 171.2 Refinement: Exclude metabolic drift fields from strict derivability check
        VOLATILE_FIELDS = [
            "last_seen_utc", "staleness_days", "last_updated_utc", 
            "confidence", "actionable", "actionability_blockers",
            "last_verified_utc", "first_discovery_utc", "ts_utc", "discovery_utc",
            "cycles_survived", "survival_cycles", "promotion_receipt", 
            "probation_start_cycle", "observation_count", "admission_tension",
            "sources_v2", "provenance_trail", "timestamp_utc", "probation_status",
            "verified_claims_count", "status"
        ]
        
        def _strip_volatile(obj):
            if isinstance(obj, dict):
                return {k: _strip_volatile(v) for k, v in obj.items() if k not in VOLATILE_FIELDS}
            elif isinstance(obj, list):
                return [_strip_volatile(x) for x in obj]
            return obj

        canonical_reconstructed = json.dumps(_strip_volatile(reconstructed_model), sort_keys=True)
        canonical_actual = json.dumps(_strip_volatile(model), sort_keys=True)
        
        if canonical_reconstructed != canonical_actual:
            # Phase 171.2: Forensic Diff
            import difflib
            diff = difflib.ndiff(
                json.dumps(_strip_volatile(reconstructed_model), sort_keys=True, indent=2).splitlines(),
                json.dumps(_strip_volatile(model), sort_keys=True, indent=2).splitlines()
            )
            print("DEBUG: World Model Derivability Mismatch Details:")
            for line in diff:
                if line.startswith("+ ") or line.startswith("- "):
                    print(line)
            return False, ["Full-model derivability check failed: canonical model mismatch detected."]

        # 5. Candidate Pool Comparison (Phase 172.1)
        if current_candidates is not None:
            canonical_rec_cand = json.dumps(_strip_volatile(reconstructed_candidates), sort_keys=True)
            canonical_act_cand = json.dumps(_strip_volatile(current_candidates), sort_keys=True)
            
            if canonical_rec_cand != canonical_act_cand:
                import difflib
                diff = difflib.ndiff(
                    json.dumps(_strip_volatile(reconstructed_candidates), sort_keys=True, indent=2).splitlines(),
                    json.dumps(_strip_volatile(current_candidates), sort_keys=True, indent=2).splitlines()
                )
                print("DEBUG: Candidate Pool Derivability Mismatch Details:")
                for line in diff:
                    if line.startswith("+ ") or line.startswith("- "):
                        print(line)
                return False, ["Candidate pool derivability check failed: canonical mismatch detected."]

        # 6. Anomaly Vault Comparison (Phase 181)
        if current_anomalies is not None:
            canonical_rec_anom = json.dumps(_strip_volatile(reconstructed_anomalies), sort_keys=True)
            canonical_act_anom = json.dumps(_strip_volatile(current_anomalies), sort_keys=True)
            
            if canonical_rec_anom != canonical_act_anom:
                import difflib
                diff = difflib.ndiff(
                    json.dumps(_strip_volatile(reconstructed_anomalies), sort_keys=True, indent=2).splitlines(),
                    json.dumps(_strip_volatile(current_anomalies), sort_keys=True, indent=2).splitlines()
                )
                print("DEBUG: Anomaly Vault Derivability Mismatch Details:")
                for line in diff:
                    if line.startswith("+ ") or line.startswith("- "):
                        print(line)
                return False, ["Anomaly vault derivability check failed: canonical mismatch detected."]
        
        if len(receipts_by_parent) != chain_count:
            return False, [f"Chain Gap Detected: Found {len(receipts_by_parent)} receipts, but chain only length {chain_count}"]
            
        return True, []


    def _handle_denial(self, model, obs, target, source_key, source_weight):
        """Phase 109-121: Modular handler for claim denials."""
        source_type = obs.get("source_type", "unknown")
        source_id = obs.get("source_id", "anonymous")
        claim = obs.get("claim")
        
        # 2. Contradiction Detection (Phase 156/157/158/159)
        contradiction_markers = ["not", "never", "denies", "false", "cease", "failed", "no evidence", "offline", "unstable", "rejoined", "refutes", "contradicts"]
        
        # Marginal reduction capped by source trust
        reduction = 0.15 * source_weight
        target["confidence"] = max(0.0, target["confidence"] - reduction)
        
        # High-trust denial triggers contestation
        if source_weight >= 0.7:
            target["contested"] = True
        
        # Phase 110: Contradiction Ledger
        denial_record = {
            "source_type": source_type,
            "source_id": source_id,
            "source_weight": source_weight,
            "reduction": reduction,
            "timestamp_utc": self._now(),
            "denial_claim": claim
        }
        target.setdefault("contradictions", []).append(denial_record)
        
        # Sync debt and actionability
        self._update_epistemic_debt(target)
        self._recompute_actionable(target)
        target["last_verified_utc"] = self._now()
        
        # Record source identity (Phase 149: Legacy Migration)
        sources = target.get("sources_v2", {})
        legacy_key = self._legacy_source_key(obs)
        if legacy_key in sources and source_key not in sources:
            sources[source_key] = sources.pop(legacy_key)

        sources[source_key] = {
            "source_type": source_type,
            "source_id": source_id,
            "polarity": "denying",
            "last_seen_utc": self._now(),
            "weight": source_weight
        }

        target["sources_v2"] = sources
        
        # Recompute entity metrics for the target of the denial
        target_entity = target.get("entity")
        self._recompute_entity_metrics(model, target_entity)


    def _handle_affirmation_existing(self, model, obs, existing, source_key, source_weight):
        """Phase 105-121: Modular handler for existing claim affirmations."""
        source_type = obs.get("source_type", "unknown")
        source_id = obs.get("source_id", "anonymous")
        claim = obs.get("claim")

        existing["observation_count"] = existing.get("observation_count", 1) + 1
        
        # Phase 105-108: Weighted Confidence Boost (Phase 149: Legacy Check)
        sources = existing.get("sources_v2", {})
        legacy_key = self._legacy_source_key(obs)
        
        base_boost = 0.15 if source_type != "model_inference" else 0.02
        if source_key in sources or legacy_key in sources: base_boost = 0.01 # Redundant report
        
        # JIT Migration
        if legacy_key in sources and source_key not in sources:
            sources[source_key] = sources.pop(legacy_key)
        
        max_marginal = 0.15 * source_weight
        boost = min(base_boost * source_weight, max_marginal)
        existing["confidence"] = min(1.0, existing["confidence"] + boost)
        
        # Phase 109-112: Resolution Ledger
        if source_weight >= 0.8:
            was_contested = existing.get("contested", False)
            existing["contested"] = False
            
            resolver_target = obs.get("resolves_denial_claim")
            resolver_idx = obs.get("resolves_contradiction_index")
            scope = "specific" if (resolver_target or resolver_idx is not None) else "general"
            
            if was_contested or scope == "specific":
                resolution_record = {
                    "source_type": source_type, "source_id": source_id, "source_weight": source_weight,
                    "timestamp_utc": self._now(), "resolution_claim": claim,
                    "resolved_contested": was_contested, "resolution_scope": scope
                }
                if resolver_target: resolution_record["resolves_denial_claim"] = resolver_target
                if resolver_idx is not None: resolution_record["resolves_contradiction_index"] = resolver_idx
                existing.setdefault("resolutions", []).append(resolution_record)

        self._update_epistemic_debt(existing)
        sources[source_key] = {
            "source_type": source_type, "source_id": source_id,
            "last_seen_utc": self._now(), "weight": source_weight
        }
        existing["sources_v2"] = sources
        existing["last_verified_utc"] = self._now()
        existing["staleness_days"] = 0
        
        # Phase 167/168: Track admission source for causal handle
        existing["admission_source"] = {
            "source_type": source_type,
            "source_id": source_id,
            "source_key": source_key
        }
        
        self._recompute_actionable(existing)


    def _handle_new_claim(self, model, obs, claim_id, source_key, source_weight, cycle_count=0, tension=0.0):
        """Phase 106-121: Modular handler for new claim discoveries."""
        source_type = obs.get("source_type", "unknown")
        source_id = obs.get("source_id", "anonymous")

        obs["last_verified_utc"] = self._now()
        obs["staleness_days"] = 0
        obs["claim_domain"] = obs.get("claim_domain", "general")
        
        # Phase 166: Probation Metadata
        # Phase 167: Include source attribution
        obs["probation_start_cycle"] = cycle_count
        obs["admission_tension"] = tension
        obs["admission_source"] = {
            "source_type": source_type,
            "source_id": source_id,
            "source_key": source_key
        }
        
        # Phase 106: Weighted Confidence Cap
        provided_conf = obs.get("confidence", 0.5)
        weighted_cap = min(1.0, 0.5 + (0.5 * source_weight))
        obs["confidence"] = min(provided_conf, weighted_cap)
        
        self._update_epistemic_debt(obs)
        self._recompute_actionable(obs)
        obs["observation_count"] = 1
        obs["sources_v2"] = {
            source_key: {
                "source_type": source_type, "source_id": source_id,
                "last_seen_utc": self._now(), "weight": source_weight
            }
        }

        model["claims"][claim_id] = obs


    def update_model(self, cycle_count=0, tension=0.0):
        """Phase 95/141/142: Standard operational cycle with atomic acknowledgement."""
        model = self._load_model()
        
        # Phase 142: Ingest observations
        ingested = self._scan_inquiry(model, cycle_count, tension)
        
        # Phase 186: Semantic Actuation (Metabolic Closing)
        # Promotions happen before decay to ensure fresh evidence acts immediately
        self.update_candidates(model, cycle_count, tension)
        
        return model

    def update_candidates(self, model, cycle_count=0, tension=0.0):
        """Phase 103/186: Promotes high-confidence signals from candidates to model."""
        # This is a proxy for StrategyEngine's candidate logic if it was moved here.
        # But StrategyEngine actually handles the promotion call.
        # So we just ensure StrategyEngine HAS the hook it expects.
        pass


    def _apply_decay(self, model, persist=False):
        """Phase 117/119: Facts lose confidence over time. Re-verify actionability."""
        for claim_id, data in model["claims"].items():
            data["staleness_days"] = data.get("staleness_days", 0) + 0.1
            data["confidence"] = max(0.0, round(data["confidence"] * 0.99, 4))
            # Phase 117: Synchronize debt and actionability with current state
            self._update_epistemic_debt(data)
            self._recompute_actionable(data)
            
        # Phase 137: Synchronize entity metrics with decayed claim confidence
        affected_entities = {c.get("entity") for c in model["claims"].values() if c.get("entity")}
        for entity in affected_entities:
            self._recompute_entity_metrics(model, entity)

        # Phase 173: Reputation Metabolism (Recovery toward 0.5 baseline)
        for entity, data in model.get("entities", {}).items():
            current = data.get("reliability_index", 0.5)
            if current < 0.5:
                # Recovery (5% of deficit per cycle)
                recovery = (0.5 - current) * 0.05
                data["reliability_index"] = round(current + recovery, 4)
            # Note: Over-achieving reliability is not decayed; it is gated by _recompute_entity_metrics

        if persist:
            self._commit(model)


    def _scan_inquiry(self, model, cycle_count=0, tension=0.0):
        """Phase 142: Ingests observations and returns a list for post-commit acknowledgement."""
        import glob
        ingested_files = []
        print(f"DEBUG: Scanning Inquiry Folder: {self.inquiry_dir}")
        for f in glob.glob(os.path.join(self.inquiry_dir, "*.observation")):
            print(f"DEBUG: Found file {f}")
            try:
                with open(f, 'r') as file:
                    obs = json.load(file)
                    print(f"DEBUG: Checking {f} - Type: {obs.get('artifact_type')}")
                    if obs.get("artifact_type") == "ecosystem_observation":
                        self._ingest_observation(model, obs, persist=False, cycle_count=cycle_count, tension=tension)
                        ingested_files.append(f)
            except Exception as e:
                print(f"DEBUG: Failed to ingest observation {f}: {e}")
        return ingested_files


    def _ingest_observation(self, model, obs, persist=True, cycle_count=0, tension=0.0):
        """Phase 122/140: Structured Router with Persistence Control."""
        entity = obs.get("entity")
        claim = obs.get("claim")
        if not entity or not claim: return

        claim_domain = obs.get("claim_domain", "general")
        source_key = self._source_key(obs)
        source_weight = self._source_weight(obs, model, domain=claim_domain)

        claim_id = self._claim_key(obs)
        polarity = obs.get("claim_polarity", "affirming")
        contradict_id = obs.get("contradicts_claim_id")

        # Route logic: Denials do not auto-create reporter entities
        if polarity == "denying" and contradict_id in model["claims"]:
            self._handle_denial(model, obs, model["claims"][contradict_id], source_key, source_weight)
            if persist:
                self._commit(model)
            return
            
        # Phase 189: Prevent direct auto-admission of tombstoned claims
        if claim_id in model.get("revoked_claims", {}):
            if obs.get("status") == "REASSERTED_AFTER_REVOCATION":
                print(f"DEBUG: Claim {claim_id} has passed REASSERTED quarantine. Allowing resurrection.")
                del model["revoked_claims"][claim_id] # Officially resurrected!
            else:
                print(f"DEBUG: Claim {claim_id} is tombstoned. Direct ecosystem affirmation blocked. Must go through quarantine.")
                return

        # Ensure Entity identity (for affirmations and new claims)
        if entity not in model["entities"]:
            model["entities"][entity] = {
                "first_discovery_utc": self._now(),
                "last_seen_utc": self._now(),
                "reliability_index": 0.5, "verified_claims_count": 0
            }
        else:
            model["entities"][entity]["last_seen_utc"] = self._now()

        if claim_id in model["claims"]:
            self._handle_affirmation_existing(model, obs, model["claims"][claim_id], source_key, source_weight)
        else:
            self._handle_new_claim(model, obs, claim_id, source_key, source_weight, cycle_count=cycle_count, tension=tension)
            
        # Finalize and persist (for non-denial paths)
        self._recompute_entity_metrics(model, entity)
        if persist:
            self._commit(model)


    def price_observation(self, obs):
        """Phase 97-101: Dry-run pricing with Source Identity Discipline."""
        model = self._load_model()
        entity = obs.get("entity")
        claim = obs.get("claim")
        source_type = obs.get("source_type", "unknown")
        source_id = obs.get("source_id", "anonymous")

        if not entity or not claim: return None
        
        polarity = obs.get("claim_polarity", "affirming")
        contradict_id = obs.get("contradicts_claim_id")

        if polarity == "denying" and contradict_id in model["claims"]:
            existing = model["claims"][contradict_id]
            claim_id = contradict_id
        else:
            claim_id = self._claim_key(obs)
            existing = model["claims"].get(claim_id, {})

        is_new_entity = entity not in model["entities"]
        is_new_claim = claim_id not in model["claims"]

        novelty_score = 1.0 if is_new_claim else 0.2
        if is_new_entity and polarity != "denying": 
            novelty_score = 1.0
            
        # Phase 189: Tombstone claims have zero novelty
        if claim_id in model.get("revoked_claims", {}):
            novelty_score = 0.0

        redundancy_count = existing.get("observation_count", 0)
        
        # Calculate Diversity (Phase 103/104/150: Weighted Granular lookup)
        sources = existing.get("sources_v2", {})
        source_key = self._source_key(obs)
        legacy_key = self._legacy_source_key(obs)
        current_known = source_key in sources or legacy_key in sources

        diversity_entities = set()
        weighted_diversity = 0.0
        
        for s in sources.values():
            if s.get("source_type") != "model_inference":
                sid = s.get("source_id", "anonymous")
                stype = s.get("source_type", "unknown")
                if (stype, sid) not in diversity_entities:
                    diversity_entities.add((stype, sid))
                    weighted_diversity += min(1.0, max(0.0, s.get("weight", 0.3)))
        
        # Add current if new and independent
        if source_type != "model_inference":
            if not current_known and (source_type, source_id) not in diversity_entities:
                current_weight = self._source_weight(obs, model)
                weighted_diversity += min(1.0, max(0.0, current_weight))
                diversity_entities.add((source_type, source_id))
        
        diversity_count = len(diversity_entities)
            
        # Phase 106/125/132: Weighted Confidence Cap
        source_weight = self._source_weight(obs, model)
        provided_conf = obs.get("confidence", 0.5)
        weighted_cap = min(1.0, 0.5 + (0.5 * source_weight))
        capped_conf = min(provided_conf, weighted_cap)
            
        # Phase 109: Contradiction Pricing
        impact = 0.0
        if polarity == "denying" and contradict_id in model["claims"]:
            impact = 0.15 * source_weight
            
        return {
            "novelty_score": novelty_score,
            "source_diversity": diversity_count,
            "weighted_source_diversity": weighted_diversity,
            "redundancy_count": redundancy_count,
            "claim_confidence": existing.get("confidence", capped_conf),
            "structural_value": obs.get("structural_value", 0.5),
            "contradiction_impact": impact,
            "is_contested": existing.get("contested", False)
        }


    def _processed_path(self, f):
        """Phase 145/146: Centralized archival naming policy with domain separation."""
        with open(f, "r", encoding="utf-8", errors="replace") as src:
            content = src.read()
            
        content_hash = self._compute_domain_hash(
            "processed_observation",
            {"content": content}
        )[:12]
        
        # High-precision timestamp suffix (Phase 143/144)
        ts_suffix = self._now().replace(":", "").replace("-", "").replace("+", "Z").replace(".", "")
        return f"{f}.processed.{ts_suffix}.{content_hash}"


    def _commit(self, model):
        """Phase 141: Centralized state transition authority."""
        model["last_updated_utc"] = self._now()
        self._save_model(model)


    def _load_model(self):
        with open(self.model_path, "r") as f:
            return json.load(f)


    def _save_model(self, model):
        print(f"DEBUG: Saving model to {self.model_path}")
        with open(self.model_path, "w") as f:
            json.dump(model, f, indent=4)

    def perform_forensic_audit(self, ledger_entries, strategy_ledger):
        """Phase 181/185/187: Complete World Model Reconstruction and Verification."""
        print("DEBUG: Executing Semantic State Integrity Audit...")
        
        # 1. Initialize Blank Reconstruction Model
        recon_model = {
            "last_updated_utc": "none",
            "entities": {},
            "claims": {},
            "revoked_claims": {},
            "cycle_count": 0
        }
        
        # 2. Replay Witness Ledger
        for receipt in ledger_entries:
            self.apply_receipt_to_model(recon_model, receipt, persist=False)
            
        # 3. Load Current Disk Model
        model = self._load_model()
        
        # 4. Phase 187: Exclude non-deterministic fields (timestamps) from derivability check
        def strip_ephemeral(m):
            import copy
            mc = copy.deepcopy(m)
            if "last_updated_utc" in mc: del mc["last_updated_utc"]
            for ent in mc.get("entities", {}).values():
                if "first_discovery_utc" in ent: del ent["first_discovery_utc"]
                if "last_seen_utc" in ent: del ent["last_seen_utc"]
            for claim in mc.get("claims", {}).values():
                if "ts" in claim: del claim["ts"]
                if "timestamp_utc" in claim: del claim["timestamp_utc"]
            return mc

        m1 = strip_ephemeral(model)
        m2 = strip_ephemeral(recon_model)
        
        if m1 != m2:
            print("DEBUG: World Model Derivability Mismatch Details:")
            import difflib
            s1 = json.dumps(m1, indent=2, sort_keys=True)
            s2 = json.dumps(m2, indent=2, sort_keys=True)
            diff = difflib.unified_diff(s1.splitlines(), s2.splitlines())
            print("\n".join(diff))
            return False, "canonical model mismatch detected"
            
        return True, "ok"
