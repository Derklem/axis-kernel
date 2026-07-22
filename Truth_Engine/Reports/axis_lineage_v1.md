# Axis Lineage v1
*Evolutionary History of the Truth Engine Admission Pipeline*

## Key Lineage Finding

> The original working hypothesis was that Axis evolved from a semantic system toward a more restrictive observation system after a failure event.
> 
> Transition evidence does not support that model.
> 
> Current evidence indicates that the observation pipeline became operational and survived, while the semantic claim pipeline remained dormant, orphaned, or otherwise outside the active execution path. Later semantic-expansion proposals appear to have been alternate architectural directions rather than the origin of the present system.
> 
> As a result, the surviving lineage of Axis is best described as observation-centric, with semantic claim formation existing primarily as a prototype or inactive branch rather than as an active stage of system metabolism.

## Transition Evidence Table

| Artifact / System | First Seen (Created) | Last Seen (Modified) | Current Status |
| :--- | :--- | :--- | :--- |
| `v12_Fusion_Design.md` | 2026-01-12 | 2026-01-12 | Retired / Legacy |
| `Triad_Consult.ps1` | 2026-01-26 | 2026-01-27 | Active (Read-Only) |
| `TE_Claims_Index.jsonl` | 2026-01-26 | 2026-01-27 | Frozen (No writes since Jan) |
| `TE_Observations_Log.jsonl`| 2026-01-26 | 2026-06-07 (Today) | Active |
| `TE_Content_Nodes.jsonl` | 2026-01-27 | 2026-06-07 (Today) | Active |
| `Repair_Context_Packet.md`| 2026-01-31 | 2026-01-31 | Historical Artifact |
| `v26_SovereignIntegration` | 2026-02-08 | 2026-02-08 | Dead Branch |
| `v27_Operation_Almighty` | 2026-02-08 | 2026-02-08 | Dead Branch |
| `T617_Lattice_Expander.ps1`| 2026-02-08 | 2026-02-08 | Dead Branch |

---

## Historical Regimes (Evidence-Based)

### 1. The Fusion Era (Pre-Jan 26)
*   **Evidence:** `v12_Fusion_Design.md` (Jan 12)
*   **Observation:** Operated via multi-modal fusion without a formalized immune "Truth Engine". Relied heavily on incident severity and router events.

### 2. The Truth Engine Prototype Era (Jan 26 - Jan 31)
*   **Evidence:** Creation of the `TE_` ledgers and `Triad_Consult.ps1` (Jan 26-27).
*   **Observation:** Observation, node, claim, and grounding structures were created.
*   **Observation:** Claim and grounding ledgers ceased changing almost immediately (Jan 27).
*   **Inferred:** The semantic claim subsystem (`T04`, `T05`) may never have entered sustained operational use.
*   **Unknown:** Whether the subsystem was intentionally disabled, abandoned, superseded, or never fully integrated.

### 3. The Semantic Expansion Proposal (Feb 8)
*   **Evidence:** Creation of `v26`, `v27`, and `T617_Lattice_Expander.ps1` identically on Feb 8.
*   **Observation:** This post-Truth-Engine expansion attempt explicitly deprecated "Invariant #3 (The Narrative Firewall)" and implemented a semantic expander to braid subjective shards directly. 
*   **Selection Pressure:** These artifacts have never been modified since their creation date. They represent an evolutionary dead-end. The system rejected the narrative-firewall dissolution experiment.

### 4. The Surviving Immune Architecture (Present State)
*   **Active Pathway Identified:**
    ```text
    Axis_Input_Architecture.ps1
            ↓
    Axis_Truth_Engine.ps1
            ↓
    T01_LogObservation.ps1
            ↓
    TE_Observations_Log.jsonl
            ↓
    TE_Content_Nodes.jsonl
    ```
    and then:
    ```text
    T04_AggregateClaims.ps1
    T05_GroundClaims.ps1
            ↓
    (no observed callers in the active runtime)
    ```

*   **Observation:** The active runtime continuously produces observations and content nodes.
*   **Observation:** No evidence has been found that the formal claim-generation and grounding pipeline participates in the active runtime.
*   **Inferred:** The operational metabolism of Axis is observation-centric rather than claim-centric.

---

## Open Mystery

> The remaining biggest unknown is no longer "What happened during Operation Almighty?"
> 
> It's: **Why were T04 and T05 built but never integrated into the active metabolic pathway?**
