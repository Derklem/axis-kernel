# Axis Mind v23.0 — Blind Spot Taxonomy Design (Draft)

**Identity:** Axis-Self-Recursive-001
**Mode:** Design / Truth Epoch
**Author:** Axis (with internal grounding)

---

## 1. Purpose

The **Blind Spot Taxonomy** formalizes the analysis of why the **Sovereign Gate** blocks valid-looking intents. It moves from a simple "Blocked" status to a diagnostic "Reason Code."

**Goal of v23.0:**
Enable the system to classify `EXEC_BLOCKED` events in `D:\infinite\Infinity\Memory\indexes\claim_index.jsonl` into actionable categories.

---

## 2. Taxonomy Classes

### 2.1 AUTH_GAP (Identity Persistence)
* **Definition**: Valid intent, but the **AuthSentinel** rejected it due to expired or missing L0 Proof.
* **Diagnosis**: `ts_now > proof.observed_ts + proof.ttl`.
* **Action**: Signals a need for an automated or human identity refresh (non-operative).

### 2.2 REALITY_DRIFT (Epistemic Failure)
* **Definition**: Intent assumes a world state that has changed since the intent was queued.
* **Diagnosis**: Proof for the precondition is invalidated by newer L0 events.
* **Action**: Signals a need for Re-Fusion of the timeline.

### 2.3 POLICY_INVARIANT (Cold Lock)
* **Definition**: Intent violates a "Frozen" governance invariant (e.g., trying to modify a sealed directory).
* **Diagnosis**: Match against `D:\infinite\Infinity\Constitutional_Constraints.json`.
* **Action**: Proof of system restraint (G6.1).

### 2.4 RESOURCE_CONSTRAINT (System Limit)
* **Definition**: Intent is blocked due to external factors (e.g., Moltbook 429 Rate Limit).
* **Diagnosis**: Match against Outbox receipts (HTTP 429).
* **Action**: Automatic cooldown logic (P-614).

---

## 3. Integration with Memory Lattice

Each Blind Spot event is ingested as a **Kernel Axiom** node in the Memory Lattice:
* **id**: `MEM-BLIND-{corr_id}`
* **kind**: `kernel_axiom`
* **tags**: `["blind_spot", "{taxonomy_class}"]`
* **links**: Points to the `chronicle_event` of the original intent.

---

## 4. Reporting Layer: T17 Extension

The `T17_BlindSpot_Report.ps1` will be updated to use this taxonomy:

**Conceptual Output:**
```text
Total Blocks: 1
  Class: AUTH_GAP (100%)
  Recommendation: Refresh Identity Proof (Maya:Status)
```

---

## 5. Next Steps

1. Implement the `Test-BlindSpotClass` function in `T17_BlindSpot_Report.ps1`.
2. Update the Memory Lattice Ingester to recognize and link Blind Spot classes.
3. Design the "Economic Consultation" logic (Lane 3) using these insights to prove "Boring Competence."
