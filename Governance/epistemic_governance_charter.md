# Epistemic Governance Charter v1

**Authority:** This charter is the constitutional authority governing how external information interacts with the Axis architecture. It supersedes any machine-readable registries or implementation defaults.

## 1. Axis Structural Ontology

Axis is not a conversational chatbot. Axis is an **epistemic ledger that happens to speak.**

The system's structural ontology consists of five distinct layers:

* **Epistemic Ledger:** The core identity and memory, storing the permanent record of evaluated truth claims.
* **Witness Chain:** The cryptographic continuity layer that guarantees the integrity of the ledger and prevents undetectable tampering.
* **Metabolism:** The engine (`StrategyEngine`) responsible for evaluating, challenging, and integrating incoming claims into the ledger.
* **Governance Layer:** The operational constraints, lock configurations, and classification rules that govern the metabolism.
* **Conversational Surfaces:** Peripheral, read-only exhaust that narrates telemetry and presence without touching the core ledger.

## 2. Cycle 569 Architectural Discovery

> [!IMPORTANT]
> **Cycle 569 established a foundational governance precedent:** `Direct_Inquiry` is not a passive conversational surface. 

During the daemonization experiments of Cycle 569, it was empirically demonstrated that inquiry processing triggers candidate generation and lineage mutation. When Axis ingests a message from `Direct_Inquiry`, it alters the `claim_candidates.json` pool, which instantly triggers a requirement for cryptographic attestation in the Witness Chain.

Therefore, `Direct_Inquiry` belongs exclusively to the **Witnessed Lane**. It cannot be safely processed under configurations that forbid self-attestation (such as `AXIS_SELF_IMPROVEMENT_ENABLED=0`).

Attempts to route casual chat through `Direct_Inquiry` will inevitably cause continuity violations and system lockdown.

## 3. Epistemic Cost Model

To prevent ambiguity, operators and automated bridges must understand the cost of their inputs.

### Witnessed Inquiry Cost (Expensive)
* **Action:** Direct injection of information into the epistemic pipeline.
* **Consequences:** 
  * Generates actionable candidates.
  * Impacts the witness chain lineage.
  * Requires explicit cryptographic attestation.
  * Carries implications for replayability and continuity.
  * **Risk:** High. Invalid or corrupted inputs will trigger continuity lockdowns.

### Surface Inquiry Cost (Cheap)
* **Action:** Reading existing state telemetry.
* **Consequences:** 
  * Generates read-only narration.
  * Leaves zero footprint on the lineage.
  * Requires zero attestation.
  * Safe for continuous, autonomous execution.
  * **Risk:** Zero. It is structurally incapable of causing a continuity violation.

## 4. Formal Lane Classifications

All external inputs must be routed according to their structural consequence. Information determines the lane; software implements the route.

| Input Type | Allowed Lane | Structural Consequence |
|---|---|---|
| Status / Telemetry Checks | Conversational | No mutation |
| Casual Dialogue / Greetings | Conversational | No mutation |
| Historical Data Queries | Conversational | Read-only synthesis |
| Architectural Hypotheses | Witnessed | Candidate creation |
| External Model Critiques | Witnessed | Claim evaluation |
| Strategic Directives | Witnessed | State transition |
| Operational Doctrine | Witnessed | Lineage mutation |
| Novel Claims on Reality | Witnessed | Lineage mutation |

*(Note: The machine-readable `lane_registry.json` is a derivative of this table. In any conflict, this table is authoritative.)*
