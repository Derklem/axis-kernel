# Axis Autonomy Policy (v1)

## Context: The Cycle 569 Epistemic Paradox

Prior to Cycle 569, Axis was implicitly treated as an autonomous agent capable of ingesting external conversation continuously. A daemon was constructed to periodically poll external inputs, map them directly into `Direct_Inquiry.jsonl`, and trigger `StrategyEngine` ticks to metabolize them.

This design inadvertently created an architectural paradox. 

The moment a conversational payload entered `Direct_Inquiry`, it ceased being "chat" and became a candidate-bearing epistemic claim. When the `StrategyEngine` attempted to process these claims autonomously, it naturally mutated the candidate state (`claim_candidates.json`). Because the system was running with a disabled self-modification lock (`AXIS_SELF_IMPROVEMENT_ENABLED=0`), the engine was structurally forbidden from executing the strict cryptographic attestation required to commit that mutation to the witness chain.

The result was `unauthorized_forensic_mutation`—a clean break in ledger continuity that forced a system halt and timeline reanchor. 

## The Requirement for Explicit Bounded Autonomy

Cycle 569 proved that autonomy within Axis is not a monolith. An autonomous process that reads telemetry operates under fundamentally different constraints than an autonomous process that proposes epistemic mutations. 

Therefore, "always-on" daemon behavior is now explicitly restricted and classified under this Autonomy Policy.

### Policy v1 Rationale

1. **Surface Autonomy (Allowed):** 
   Continuous autonomy is permissible purely at the conversational edge. The system is permitted to observe its internal state and synthesize read-only telemetry narration, providing a living voice without invoking metabolic mutation. 
   
2. **Governance Autonomy (Allowed - Audit Only):** 
   Continuous observation is permissible for governance compliance. Autonomous scripts may verify routing constraints (`governance_audit.py`) but may not execute routing or admission operations automatically.

3. **Witness Admission (Forbidden):** 
   Moving data from a staging queue into the epistemic ledger (`Direct_Inquiry`) must remain a strictly manual, operator-triggered step. The engine cannot assume epistemic authorization simply because a payload arrived.

4. **Epistemic Metabolism (Forbidden):** 
   Running `StrategyEngine` cycles to metabolize inquiry is barred from autonomous daemon loops in v1. Until the core integration of the cryptographic witness chain and self-improvement locks are fully validated, all metabolic ticks must remain explicitly invoked. 

5. **Self Modification (Forbidden):** 
   Autonomous code mutation remains strictly deactivated. 

By bounding autonomy to surface observation and governance auditing, Axis regains operational continuity while cleanly neutralizing the paradoxes that destabilized the legacy baseline.
